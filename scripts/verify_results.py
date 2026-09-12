#!/usr/bin/env python3
"""Validate saved experiment histories without connecting to Cassandra."""
import argparse
import json
from collections import Counter
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from checks import classify

def verify(run):
    def load(name):
        return json.loads((run/name).read_text())
    assert load('completion.json')['completed'] is True
    env=load('environment.json')
    trials=load('trials.json')
    assert len(trials)==3*len(env['configs'])*4*env['repeats']
    assert len({t['key'] for t in trials})==len(trials)
    baseline={}
    cluster=load('initial_cluster.json')
    coordinators={o['node']:o['coordinator'] for o in cluster['schema'] if o['status']=='ok'}
    for scenario in ('normal','node_failure','partition'):
        init=load(scenario+'_initialization.json')
        assert len(init)==len(env['configs'])*4*env['repeats']
        assert all(o['status']=='ok' and o['cl']=='ALL' for o in init)
        initialized={o['params'][0] for o in init}
        baseline.update({o['params'][0]:o['params'][1] for o in init})
        assert initialized=={t['key'] for t in trials if t['scenario']==scenario}
    for trial in trials:
        operations=trial['operations']
        for a,b in zip(operations,operations[1:]):
            assert a['end_ns']<=b['start_ns'], 'Session operations overlap'
        w,r=trial['config'].split('/')
        timestamps=[o['params'][0] for o in operations if o['query'].startswith('UPDATE')]
        assert timestamps[0]>baseline[trial['key']]
        assert all(a<b for a,b in zip(timestamps,timestamps[1:]))
        for op in operations:
            assert op['cl']==(r if op['query'].startswith('SELECT') else w)
            assert trial['key'] in op['params']
            assert op['start_ns']<=op['end_ns']
            if op['status']=='ok':
                assert op['coordinator']==coordinators[op['node']]
            if op['status']=='ok' and op['query'].startswith('SELECT'):
                assert set(op['value'])=={'a','b'}
                assert all(v in (0,1) for v in op['value'].values())
        verdict=classify(trial['model'],operations)
        if trial['model']=='WFR' and (operations[1]['status']!='ok' or operations[1]['value']['a']!=1):
            verdict='inconclusive'
        assert verdict==trial['verdict']
    controls=load('read_repair.json')
    assert len(controls)==2*env['repeats']
    for trial in controls:
        assert trial['write']['cl']=='ONE'
        assert trial['first']['cl']==trial['second']['cl']=='QUORUM'
    print(f'Validated {len(trials)} matrix trials and {len(controls)} read-repair controls.')
    print(dict(Counter(t['verdict'] for t in trials)))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    verify(parser.parse_args().results)
