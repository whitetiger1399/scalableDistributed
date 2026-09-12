#!/usr/bin/env python3
"""Host-side orchestration. Only touches this Compose project's containers."""
import argparse
import datetime
import itertools
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
CONFIGS = ['ONE/ONE', 'QUORUM/ONE', 'ONE/QUORUM', 'QUORUM/QUORUM', 'ALL/ALL']
NODES = ('n1', 'n2', 'n3')

def command(args, data=None, check=True):
    p = subprocess.run(args, input=data, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f'{shlex.join(args)}\n{p.stdout}\n{p.stderr}')
    return p.stdout.strip()

def compose(*args, **kwargs):
    executable = os.environ.get('COMPOSE_BIN')
    base = [executable] if executable else ['docker', 'compose']
    return command(base + ['-f', str(ROOT/'compose.yaml')] + list(args), **kwargs)

def worker(req):
    return json.loads(compose('exec', '-T', 'client', 'python', 'src/worker.py', data=json.dumps(req)))

def assert_ok(records):
    if isinstance(records, dict):
        records = [records]
    bad = [r for r in records if r['status'] != 'ok']
    if bad:
        raise RuntimeError(json.dumps(bad, indent=2))

def node_exec(node, *args, **kwargs):
    return compose('exec', '-T', '-u', 'root', node, *args, **kwargs)

def topology(blocked):
    """Block storage traffic, retaining CQL 9042 and client connectivity."""
    ips = {}
    for node in NODES:
        cid = compose('ps', '-q', node)
        info = json.loads(command(['docker','inspect',cid]))[0]
        ips[node] = next(iter(info['NetworkSettings']['Networks'].values()))['IPAddress']
    # Add new blocks BEFORE removing old ones: never briefly heal a transition.
    current, desired = {}, {n: [] for n in NODES}
    for node in NODES:
        node_exec(node, 'iptables', '-N', 'LAB_FAULT', check=False)
        if '-A OUTPUT -j LAB_FAULT' not in node_exec(node,'iptables','-S','OUTPUT'):
            node_exec(node, 'iptables', '-I', 'OUTPUT', '1', '-j', 'LAB_FAULT')
        current[node] = [shlex.split(line)[2:] for line in node_exec(node,'iptables','-S','LAB_FAULT').splitlines() if line.startswith('-A ')]
    for left, right in blocked:
        for source, dest in ((left,right),(right,left)):
            for port_flag in ('--dports', '--sports'):
                desired[source].append(['-d', ips[dest]+'/32', '-p', 'tcp', '-m', 'multiport', port_flag, '7000,7001', '-j', 'DROP'])
    for node in NODES:
        for rule in desired[node]:
            if rule not in current[node]:
                node_exec(node,'iptables','-A','LAB_FAULT',*rule)
    for node in NODES:
        for rule in current[node]:
            if rule not in desired[node]:
                node_exec(node,'iptables','-D','LAB_FAULT',*rule)
    return {node: node_exec(node, 'iptables', '-L', 'LAB_FAULT', '-v', '-n') for node in NODES}

def wait_ready(timeout=600):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        try:
            status = node_exec('n1', 'nodetool', 'status')
            if sum(line.startswith('UN ') for line in status.splitlines()) == 3:
                response = worker({'action':'schema'})
                assert_ok(response)
                return {'nodetool':status, 'schema':response}
        except RuntimeError:
            pass
        time.sleep(5)
    raise TimeoutError('Cluster did not reach three live nodes; inspect docker compose logs.')

def run(repeats):
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT/'results'/stamp
    out.mkdir(parents=True)
    def save(name, value):
        (out/name).write_text(json.dumps(value, indent=2)+'\n')
    save('environment.json', dict(started_utc=stamp, repeats=repeats, configs=CONFIGS,
        docker=json.loads(command(['docker','info','--format','{{json .}}'])),
        compose=compose('version'), images=json.loads(command(['docker','image','inspect',
             'consistency-lab-cassandra:5.0.9', 'cassandra-consistency-lab-client'])),
        client=compose('exec','-T','client','pip','freeze')))
    save('source_hashes.json', {str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [ROOT/'compose.yaml', ROOT/'Dockerfile.cassandra', ROOT/'Dockerfile.client',
                     ROOT/'src/worker.py', ROOT/'src/checks.py', ROOT/'report/predictions.md']})
    all_trials = []
    fault_log = []
    try:
        save('initial_cluster.json', wait_ready())
        save('runtime_checks.json', {n:dict(hints=node_exec(n,'nodetool','statushandoff'),
            java=node_exec(n,'java','--version'),iptables=node_exec(n,'iptables','--version')) for n in NODES})
        for scenario in ('normal', 'node_failure', 'partition'):
            print(f'Running {scenario}', flush=True)
            prefix = f'{stamp}:{scenario}'
            ts = time.time_ns()//1000
            keys = [f'{prefix}:{config}:{model}:{i}' for config in CONFIGS
                    for model in ('RYW','MR','MW','WFR') for i in range(repeats)]
            initialization = worker(dict(action='init', keys=keys, ts=ts))
            assert_ok(initialization)
            save(f'{scenario}_initialization.json', initialization)
            if scenario == 'node_failure':
                compose('kill', '-s', 'SIGKILL', 'n3')
                time.sleep(15)
                fault_log.append(dict(scenario=scenario, action='SIGKILL n3', status=node_exec('n1','nodetool','status')))
            elif scenario == 'partition':
                rules = topology([('n1','n3'),('n2','n3')])
                time.sleep(15)
                fault_log.append(dict(scenario=scenario, rules=rules,
                    status={n:node_exec(n,'nodetool','status') for n in NODES}))
            trials = worker(dict(action='batch', scenario=scenario, prefix=prefix,
                                 configs=CONFIGS, repeats=repeats, ts=ts+1000000))
            all_trials += trials
            save('trials.json', all_trials)
            if scenario == 'node_failure':
                compose('start','n3')
                wait_ready()
            if scenario == 'partition':
                fault_log.append(dict(scenario=scenario, counters={n:node_exec(n,'iptables','-L','LAB_FAULT','-v','-n') for n in NODES}))
                topology([])
                wait_ready()
        save('faults.json', fault_log)
        # A controlled change of read quorums exposes the role of read repair.
        special = []
        for table in ('blocking','no_repair'):
            for i in range(repeats):
                print(f'Read repair {table}, repetition {i+1}/{repeats}', flush=True)
                key = f'{stamp}:repair:{table}:{i}'
                ts = time.time_ns()//1000
                assert_ok(worker(dict(action='init',keys=[key],ts=ts,tables=[table])))
                topology([('n1','n3'),('n2','n3')])
                time.sleep(12)
                write = worker(dict(action='op',kind='write',node='n3',key=key,column='a',value=1,ts=ts+1,cl='ONE',table=table))
                assert_ok(write)
                # Keep n3 isolated while disconnecting n1: no interval with full connectivity.
                topology(list(itertools.combinations(NODES,2)))
                topology([('n1','n2'),('n1','n3')])
                time.sleep(12)
                first = worker(dict(action='op',kind='read',node='n3',key=key,cl='QUORUM',table=table))
                topology(list(itertools.combinations(NODES,2)))
                topology([('n1','n3'),('n2','n3')])
                time.sleep(12)
                second = worker(dict(action='op',kind='read',node='n1',key=key,cl='QUORUM',table=table))
                special.append(dict(table=table,repetition=i,write=write,first=first,second=second))
                save('read_repair.json',special)
                topology([])
                wait_ready()
        key = f'{stamp}:timestamp'
        ts = time.time_ns()//1000
        assert_ok(worker(dict(action='init',keys=[key],ts=ts)))
        skew = [worker(dict(action='op',kind='write',node='n1',key=key,column='a',value=1,ts=ts+100,cl='ALL')),
                worker(dict(action='op',kind='write',node='n2',key=key,column='a',value=2,ts=ts+50,cl='ALL')),
                worker(dict(action='op',kind='read',node='n3',key=key,cl='ALL'))]
        save('timestamp_control.json',skew)
        save('completion.json',dict(completed=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        print(f'Results: {out}', flush=True)
    finally:
        compose('start','n3')
        topology([])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['up','run','heal','down'])
    parser.add_argument('--repeats', type=int, default=5)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    if args.action == 'up':
        print(compose('up','-d','--build'), flush=True)
        print(json.dumps(wait_ready(),indent=2))
    elif args.action == 'run':
        run(args.repeats)
    elif args.action == 'heal':
        compose('start','n3')
        topology([])
        print(json.dumps(wait_ready(),indent=2))
    else:
        print(compose('down'))  # Persistent data retained.
