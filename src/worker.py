"""Application API has no node parameter; a random gateway selects coordinators."""
import json
import logging
import socket
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import WhiteListRoundRobinPolicy, FallthroughRetryPolicy, NoSpeculativeExecutionPolicy
from cassandra.query import SimpleStatement
from checks import evaluate
from routing import RandomRouter
from experiments.workloads import operations as workload_operations

logging.basicConfig(level=logging.ERROR)
DEFAULT_NODES = ('n1', 'n2', 'n3')


class Transport:
    """Gateway's backend connections. Endpoint pinning implements a chosen route,
    and is never exposed to the application. Cassandra still selects replicas.
    """
    def __init__(self, cql_port=9042):
        self.clusters, self.sessions = [], {}
        self.cql_port = cql_port

    def session(self, node):
        if node not in self.sessions:
            ip = socket.gethostbyname(node)
            profile = ExecutionProfile(load_balancing_policy=WhiteListRoundRobinPolicy([ip]),
                retry_policy=FallthroughRetryPolicy(),
                speculative_execution_policy=NoSpeculativeExecutionPolicy(), request_timeout=12)
            cluster = Cluster([ip], port=self.cql_port, execution_profiles={EXEC_PROFILE_DEFAULT: profile},
                              protocol_version=4, connect_timeout=5)
            self.clusters.append(cluster)
            self.sessions[node] = cluster.connect()
        return self.sessions[node]

    def close(self):
        for cluster in self.clusters:
            cluster.shutdown()

    def execute(self, node, query, params=(), cl='ALL'):
        start = time.time_ns()
        started = time.monotonic_ns()
        record = dict(node=node, query=query, params=list(params), cl=cl, start_ns=start)
        try:
            future = self.session(node).execute_async(SimpleStatement(query,
                consistency_level=getattr(ConsistencyLevel, cl)), params)
            rows = list(future.result())
            record.update(status='ok', value=rows[0]._asdict() if rows else None,
                          coordinator=str(future.coordinator_host))
        except Exception as exc:
            record.update(status='error', error=type(exc).__name__, message=str(exc))
        record.update(end_ns=time.time_ns(), latency_ms=(time.monotonic_ns()-started)/1e6)
        return record

    def probe(self, node):
        record = self.execute(node, 'SELECT release_version FROM system.local', (), 'ONE')
        return {"node": node, "reachable": record["status"] == "ok",
                "coordinator": record.get("coordinator"), "error": record.get("error"),
                "message": record.get("message"), "start_ns": record["start_ns"],
                "end_ns": record["end_ns"]}


class Client:
    """Customer-facing reads and writes cannot specify a coordinator."""
    def __init__(self, transport, seed, nodes):
        self.transport = transport
        self.health = [transport.probe(node) for node in nodes]
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
    nodes = tuple(req.get('nodes', DEFAULT_NODES))
    if req['action'] == 'probe':
        return [transport.probe(node) for node in nodes]
    if req['action'] == 'schema':
        # Administration, not a measured application session.
        database = req['database']
        rf = database['replication_factor']
        queries = [f"CREATE KEYSPACE IF NOT EXISTS lab WITH replication = {{'class':'NetworkTopologyStrategy','dc1':{rf}}}"]
        queries += [f"CREATE TABLE IF NOT EXISTS lab.{t} (k text PRIMARY KEY, a int, b int) WITH read_repair='{rr}' AND speculative_retry='NONE'" for t,rr in database['read_repair_tables'].items()]
        records = [transport.execute('n1', q) for q in queries]
        records += [transport.execute(n, 'SELECT release_version, data_center, rack, host_id FROM system.local') for n in nodes]
        records += [transport.execute(n, "SELECT keyspace_name, replication FROM system_schema.keyspaces WHERE keyspace_name='lab'", (), 'ONE') for n in nodes]
        table_checks = []
        for node in nodes:
            for table, expected_repair in database['read_repair_tables'].items():
                check = transport.execute(node,
                    "SELECT table_name, read_repair, speculative_retry FROM system_schema.tables WHERE keyspace_name='lab' AND table_name=%s",
                    (table,), 'ONE')
                value = check.get('value')
                # Cassandra 5 canonicalizes CQL speculative_retry='NONE' as NEVER.
                check['expected'] = {'table_name': table, 'read_repair': expected_repair,
                                     'speculative_retry': 'NEVER'}
                check['matches_expected'] = bool(isinstance(value, dict) and
                    value.get('table_name') == table and
                    str(value.get('read_repair', '')).upper() == expected_repair and
                    str(value.get('speculative_retry', '')).upper() == 'NEVER')
                table_checks.append(check)
        records += table_checks
        status = "ok" if (all(r['status'] == 'ok' for r in records) and
                          all(r['matches_expected'] for r in table_checks)) else "error"
        return {"status": status, "records": records, "table_checks": table_checks}
    client = Client(transport, req['seed'], nodes)
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
            specifications = workload_operations(model, key, w, r, req['ts'], trial.get('table', 'blocking'))
            ops = execute_operations(client, specifications)
            result = evaluate(model, ops)
            records.append(dict(trial, operations=ops, **result))
    elif action == 'ops':
        records = []
        records = execute_operations(client, req['operations'])
    else:
        raise ValueError(action)
    return dict(seed=req['seed'], health=client.health, records=records)


def execute_operations(client, specifications):
    records = []
    for sequence, operation in enumerate(specifications):
        role = operation.get('role', 'client')
        if operation['kind'] == 'read':
            record = client.read(operation['key'], operation['cl'], operation.get('table', 'blocking'), role)
        else:
            record = client.write(operation['key'], operation['column'], operation['value'],
                                  operation['ts'], operation['cl'], operation.get('table', 'blocking'), role)
        record.update(kind=operation['kind'], sequence=sequence,
                      client_id=operation.get('client_id', 'client-1'))
        records.append(record)
    return records


if __name__ == '__main__':
    request = json.load(sys.stdin)
    backend = Transport(request.get('cql_port', 9042))
    try:
        print(json.dumps(main(request,backend),default=str))
    finally:
        backend.close()
