"""Application API delegates coordinator selection to the Cassandra driver."""
import json
import logging
import socket
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cassandra import ConsistencyLevel
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT
from cassandra.policies import (DCAwareRoundRobinPolicy, FallthroughRetryPolicy,
                                NoSpeculativeExecutionPolicy, TokenAwarePolicy,
                                WhiteListRoundRobinPolicy)
from cassandra.query import SimpleStatement
from checks import evaluate
from routing import DriverRoutingEvidence, POLICY_NAME
from experiments.workloads import operations as workload_operations

logging.basicConfig(level=logging.ERROR)
DEFAULT_NODES = ('n1', 'n2', 'n3')


class Transport:
    """Direct administrative probes plus a policy-driven application session."""

    def __init__(self, nodes=DEFAULT_NODES, cql_port=9042, local_dc='dc1'):
        self.nodes = tuple(nodes)
        self.cql_port = cql_port
        self.local_dc = local_dc
        # A Cassandra service may intentionally be absent during a node-failure
        # episode. Resolve each service independently so one missing Docker DNS
        # entry does not abort the whole worker before measurements can run.
        self.node_ips = {}
        self.resolution_errors = {}
        for node in self.nodes:
            try:
                self.node_ips[node] = socket.gethostbyname(node)
            except socket.gaierror as exc:
                self.resolution_errors[node] = str(exc)
        self.address_to_node = {ip: node for node, ip in self.node_ips.items()}
        self.direct_clusters, self.direct_sessions = [], {}
        self.application_cluster = None
        self.application_session = None
        self.routing_evidence = DriverRoutingEvidence(self.address_to_node, local_dc)

    def direct_session(self, node):
        if node not in self.node_ips:
            raise RuntimeError(
                f"CQL endpoint {node!r} is not currently resolvable: "
                f"{self.resolution_errors.get(node, 'unknown DNS error')}"
            )
        if node not in self.direct_sessions:
            ip = self.node_ips[node]
            profile = ExecutionProfile(load_balancing_policy=WhiteListRoundRobinPolicy([ip]),
                retry_policy=FallthroughRetryPolicy(),
                speculative_execution_policy=NoSpeculativeExecutionPolicy(), request_timeout=12)
            cluster = Cluster([ip], port=self.cql_port, execution_profiles={EXEC_PROFILE_DEFAULT: profile},
                              protocol_version=4, connect_timeout=5)
            self.direct_clusters.append(cluster)
            self.direct_sessions[node] = cluster.connect()
        return self.direct_sessions[node]

    def policy_session(self):
        if self.application_session is None:
            if not self.node_ips:
                raise RuntimeError('No Cassandra service names are currently resolvable')
            policy = TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=self.local_dc))
            profile = ExecutionProfile(load_balancing_policy=policy,
                retry_policy=FallthroughRetryPolicy(),
                speculative_execution_policy=NoSpeculativeExecutionPolicy(), request_timeout=12)
            self.application_cluster = Cluster(
                list(self.node_ips.values()), port=self.cql_port,
                execution_profiles={EXEC_PROFILE_DEFAULT: profile},
                protocol_version=4, connect_timeout=5)
            self.application_session = self.application_cluster.connect('lab')
        return self.application_session

    def close(self):
        if self.application_cluster is not None:
            self.application_cluster.shutdown()
        for cluster in self.direct_clusters:
            cluster.shutdown()

    def execute_on(self, node, query, params=(), cl='ALL'):
        start = time.time_ns()
        started = time.monotonic_ns()
        record = dict(node=node, query=query, params=list(params), cl=cl, start_ns=start)
        try:
            future = self.direct_session(node).execute_async(SimpleStatement(query,
                consistency_level=getattr(ConsistencyLevel, cl)), params)
            rows = list(future.result())
            record.update(status='ok', value=rows[0]._asdict() if rows else None,
                          coordinator=str(future.coordinator_host))
        except Exception as exc:
            record.update(status='error', error=type(exc).__name__, message=str(exc))
        record.update(end_ns=time.time_ns(), latency_ms=(time.monotonic_ns()-started)/1e6)
        return record

    def execute(self, query, params=(), cl='ALL', routing_key=None):
        """Execute through the driver's token-aware, DC-aware query plan."""
        start = time.time_ns()
        started = time.monotonic_ns()
        statement = SimpleStatement(
            query, consistency_level=getattr(ConsistencyLevel, cl),
            keyspace='lab' if routing_key is not None else None,
            routing_key=(routing_key.encode('utf-8') if routing_key is not None else None))
        session = self.policy_session()
        hosts = list(self.application_cluster.metadata.all_hosts())
        route = self.routing_evidence.begin(hosts)
        record = dict(query=query, params=list(params), cl=cl, start_ns=start)
        future = None
        try:
            future = session.execute_async(statement, params)
            rows = list(future.result())
            record.update(status='ok', value=rows[0]._asdict() if rows else None)
        except Exception as exc:
            record.update(status='error', error=type(exc).__name__, message=str(exc))
        coordinator = getattr(future, 'coordinator_host', None) if future is not None else None
        attempted = list(getattr(future, 'attempted_hosts', ()) or ()) if future is not None else []
        self.routing_evidence.finish(route, coordinator, attempted)
        record.update(node=route['selected_node'],
                      coordinator=str(coordinator) if coordinator is not None else None,
                      routing=route, routing_key=routing_key,
                      end_ns=time.time_ns(),
                      latency_ms=(time.monotonic_ns()-started)/1e6)
        return record

    def probe(self, node):
        record = self.execute_on(node, 'SELECT release_version FROM system.local', (), 'ONE')
        return {"node": node, "reachable": record["status"] == "ok",
                "coordinator": record.get("coordinator"), "error": record.get("error"),
                "message": record.get("message"), "start_ns": record["start_ns"],
                "end_ns": record["end_ns"]}


class Client:
    """Customer-facing reads and writes cannot specify a coordinator."""
    def __init__(self, transport, nodes):
        self.transport = transport
        self.health = [transport.probe(node) for node in nodes]
        if not any(item['reachable'] for item in self.health):
            raise RuntimeError('No client-reachable CQL endpoint')

    def execute(self, query, params=(), cl='ALL', role='application', routing_key=None):
        record = self.transport.execute(query, params, cl, routing_key)
        record.update(role=role)
        return record

    def read(self, key, cl, table='blocking', role='client'):
        return self.execute(f'SELECT a,b FROM lab.{table} WHERE k=%s', (key,), cl, role, key)

    def write(self, key, column, value, ts, cl, table='blocking', role='client'):
        assert column in ('a', 'b')
        return self.execute(f'UPDATE lab.{table} USING TIMESTAMP %s SET {column}=%s WHERE k=%s',
                            (ts, value, key), cl, role, key)


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
        records = [transport.execute_on('n1', q) for q in queries]
        records += [transport.execute_on(n, 'SELECT release_version, data_center, rack, host_id FROM system.local') for n in nodes]
        records += [transport.execute_on(n, "SELECT keyspace_name, replication FROM system_schema.keyspaces WHERE keyspace_name='lab'", (), 'ONE') for n in nodes]
        table_checks = []
        for node in nodes:
            for table, expected_repair in database['read_repair_tables'].items():
                check = transport.execute_on(node,
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
    client = Client(transport, nodes)
    action = req['action']
    if action == 'init':
        records = [client.execute(f'INSERT INTO lab.{item["table"]} (k,a,b) VALUES (%s,0,0) USING TIMESTAMP %s',
                                 (item['key'],req['ts']), 'ALL', 'initialization', item['key']) for item in req['items']]
    elif action == 'batch':
        records = []
        # Trial order is seeded and shuffled; coordinator choice remains with the driver.
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
    return dict(routing_policy=POLICY_NAME, health=client.health, records=records)


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
    routing = request.get('routing', {})
    backend = Transport(request.get('nodes', DEFAULT_NODES), request.get('cql_port', 9042),
                        routing.get('local_dc', 'dc1'))
    try:
        print(json.dumps(main(request,backend),default=str))
    finally:
        backend.close()
