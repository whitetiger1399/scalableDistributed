"""Application API has no node parameter; a random gateway selects coordinators."""
import json
import logging
import random
import socket
import sys
import time
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import WhiteListRoundRobinPolicy, FallthroughRetryPolicy, NoSpeculativeExecutionPolicy
from cassandra.query import SimpleStatement
from checks import classify
from routing import RandomRouter

logging.basicConfig(level=logging.ERROR)
NODES = ('n1', 'n2', 'n3')


class Transport:
    """Gateway's backend connections. Endpoint pinning implements a chosen route,
    and is never exposed to the application. Cassandra still selects replicas.
    """
    def __init__(self):
        self.clusters, self.sessions = [], {}

    def session(self, node):
        if node not in self.sessions:
            ip = socket.gethostbyname(node)
            profile = ExecutionProfile(load_balancing_policy=WhiteListRoundRobinPolicy([ip]),
                retry_policy=FallthroughRetryPolicy(),
                speculative_execution_policy=NoSpeculativeExecutionPolicy(), request_timeout=12)
            cluster = Cluster([ip], execution_profiles={EXEC_PROFILE_DEFAULT: profile},
                              protocol_version=4, connect_timeout=5)
            self.clusters.append(cluster)
            self.sessions[node] = cluster.connect()
        return self.sessions[node]

    def close(self):
        for cluster in self.clusters:
            cluster.shutdown()

    def execute(self, node, query, params=(), cl='ALL'):
        start = time.time_ns()
        record = dict(node=node, query=query, params=list(params), cl=cl, start_ns=start)
        try:
            future = self.session(node).execute_async(SimpleStatement(query,
                consistency_level=getattr(ConsistencyLevel, cl)), params)
            rows = list(future.result())
            record.update(status='ok', value=rows[0]._asdict() if rows else None,
                          coordinator=str(future.coordinator_host))
        except Exception as exc:
            record.update(status='error', error=type(exc).__name__, message=str(exc))
        record.update(end_ns=time.time_ns(), latency_ms=(time.time_ns()-start)/1e6)
        return record


def probe():
    """Client-side TCP health only: no fault labels or data-version knowledge."""
    observations = []
    for node in NODES:
        start = time.time_ns()
        try:
            with socket.create_connection((node, 9042), timeout=.5):
                pass
            record = dict(node=node, reachable=True)
        except OSError as exc:
            record = dict(node=node, reachable=False, error=str(exc))
        record.update(start_ns=start, end_ns=time.time_ns())
        observations.append(record)
    return observations


class Client:
    """Customer-facing reads and writes cannot specify a coordinator."""
    def __init__(self, transport, seed):
        self.transport = transport
        self.health = probe()
        self.router = RandomRouter(seed, [p['node'] for p in self.health if p['reachable']])

    def execute(self, query, params=(), cl='ALL', role='application'):
        route = self.router.select()
        record = self.transport.execute(route['selected_node'], query, params, cl)
        record.update(routing=route, role=role)
        return record

    def read(self, key, cl, table='blocking', role='client'):
        return self.execute(f'SELECT a,b FROM lab.{table} WHERE k=%s', (key,), cl, role)

    def write(self, key, column, value, ts, cl, table='blocking', role='client'):
        assert column in ('a', 'b')
        return self.execute(f'UPDATE lab.{table} USING TIMESTAMP %s SET {column}=%s WHERE k=%s',
                            (ts, value, key), cl, role)


def main(req, transport):
    if req['action'] == 'probe':
        return probe()
    if req['action'] == 'schema':
        # Administration, not a measured application session.
        queries = ["CREATE KEYSPACE IF NOT EXISTS lab WITH replication = {'class':'NetworkTopologyStrategy','dc1':3}"]
        queries += [f"CREATE TABLE IF NOT EXISTS lab.{t} (k text PRIMARY KEY, a int, b int) WITH read_repair='{rr}' AND speculative_retry='NONE'" for t,rr in [('blocking','BLOCKING'),('no_repair','NONE')]]
        records = [transport.execute('n1', q) for q in queries]
        records += [transport.execute(n, 'SELECT release_version, data_center, rack FROM system.local') for n in NODES]
        return records
    client = Client(transport, req['seed'])
    action = req['action']
    if action == 'init':
        records = [client.execute(f'INSERT INTO lab.{item["table"]} (k,a,b) VALUES (%s,0,0) USING TIMESTAMP %s',
                                 (item['key'],req['ts']), 'ALL', 'initialization') for item in req['items']]
    elif action == 'batch':
        records = []
        # Trial order is randomized separately from routing, and saved.
        for trial in req['schedule']:
            key, model = trial['key'], trial['model']
            w, r = trial['config'].split('/')
            ts = req['ts']
            ops = [client.write(key,'a',1,ts,w,role='producer' if model=='WFR' else 'client')]
            if model == 'RYW':
                ops.append(client.read(key,r))
            elif model == 'MR':
                ops += [client.read(key,r),client.read(key,r)]
            elif model == 'MW':
                ops += [client.write(key,'b',1,ts+1,w),client.read(key,r,role='observer')]
            elif model == 'WFR':
                ops += [client.read(key,r),client.write(key,'b',1,ts+1,w),client.read(key,r,role='observer')]
            else:
                raise ValueError(model)
            records.append(dict(trial,operations=ops,verdict=classify(model,ops)))
    elif action == 'ops':
        records = []
        for operation in req['operations']:
            if operation['kind']=='read':
                records.append(client.read(operation['key'],operation['cl'],operation.get('table','blocking')))
            else:
                records.append(client.write(operation['key'],operation['column'],operation['value'],
                    operation['ts'],operation['cl'],operation.get('table','blocking')))
    else:
        raise ValueError(action)
    return dict(seed=req['seed'], health=client.health, records=records)


if __name__ == '__main__':
    request = json.load(sys.stdin)
    backend = Transport()
    try:
        print(json.dumps(main(request,backend),default=str))
    finally:
        backend.close()
