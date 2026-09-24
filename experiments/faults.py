"""Project-scoped Docker/Cassandra fault injection and recovery helpers."""
import json
import os
import shlex
import subprocess
import time

NODES = ("n1", "n2", "n3")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCKER_BIN = os.environ.get("DOCKER_BIN", "docker")
COMPOSE_FILE = os.path.join(ROOT, "compose.yaml")


def configure_cluster(nodes, compose_file):
    """Select the Compose deployment used by all subsequent fault helpers."""
    global NODES, COMPOSE_FILE
    candidate = os.path.abspath(os.path.join(ROOT, compose_file))
    if os.path.dirname(candidate) != ROOT or not os.path.isfile(candidate):
        raise ValueError(f"compose file does not exist in repository root: {compose_file}")
    NODES = tuple(nodes)
    COMPOSE_FILE = candidate
    return {"nodes": list(NODES), "compose_file": os.path.basename(COMPOSE_FILE)}


def _nodes(nodes=None):
    return tuple(nodes) if nodes is not None else NODES


def command(args, data=None, check=True, timeout=60):
    result = subprocess.run(args, input=data, text=True, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(f"{shlex.join(args)}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def compose(*args, data=None, check=True, timeout=60):
    executable = os.environ.get("COMPOSE_BIN")
    base = [executable] if executable else ["docker", "compose"]
    return command(base + ["-f", COMPOSE_FILE] + list(args),
                   data=data, check=check, timeout=timeout)


def node_exec(node, *args, check=True, timeout=60):
    return compose("exec", "-T", "-u", "root", node, *args, check=check, timeout=timeout)


def container_ip(node):
    cid = compose("ps", "-a", "-q", node)
    info = json.loads(command([DOCKER_BIN, "inspect", cid]))[0]
    return next(iter(info["NetworkSettings"]["Networks"].values()))["IPAddress"]


def container_identity(node):
    cid = compose("ps", "-a", "-q", node)
    if not cid:
        raise RuntimeError(f"container is not present: {node}")
    info = json.loads(command([DOCKER_BIN, "inspect", cid]))[0]
    return {"node": node, "container_id": cid, "ip": next(iter(
        info["NetworkSettings"]["Networks"].values()))["IPAddress"],
        "running": bool(info["State"]["Running"]), "status": info["State"]["Status"]}


def parse_status(text):
    """Return nodetool rows keyed by address, independent of header/whitespace."""
    rows = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 7 and fields[0] in {"UN", "DN", "UJ", "UL", "UM", "DL"}:
            rows[fields[1]] = {"state": fields[0], "address": fields[1],
                               "host_id": fields[-2], "rack": fields[-1], "raw": line}
    return rows


def membership(observer="n1", attempts=3, timeout=30):
    """Query nodetool status, tolerating a transient slow/hung gossip call.

    nodetool can briefly hang right after a partition is torn down; a bounded,
    retried call keeps that from surfacing as a 60s subprocess timeout.
    """
    last = ""
    for _ in range(attempts):
        try:
            return node_exec(observer, "nodetool", "status", check=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            last = ""
            time.sleep(2)
    return last


def all_healthy(nodes=None):
    nodes = _nodes(nodes)
    states = {node: membership(node) for node in nodes}
    return all(len(rows := parse_status(value)) == len(nodes) and
               all(row["state"] == "UN" for row in rows.values())
               for value in states.values())


def wait_healthy(timeout_seconds=600, nodes=None):
    nodes = _nodes(nodes)
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if all_healthy(nodes):
            return {node: membership(node) for node in nodes}
        time.sleep(5)
    raise TimeoutError(f"cluster did not return to {len(nodes)} UN nodes")


def kill_node(node):
    identity = container_identity(node)
    started = time.time_ns()
    output = compose("kill", "-s", "SIGKILL", node)
    after = container_identity(node)
    if after["running"]:
        raise RuntimeError(f"container still running after SIGKILL: {node}")
    return {"action": "docker compose kill -s SIGKILL " + node,
            "node": node, "identity": identity, "after": after,
            "start_ns": started, "end_ns": time.time_ns(), "output": output}


def wait_failure(victim, victim_ip=None, timeout_seconds=90, consecutive=2, nodes=None):
    nodes = _nodes(nodes)
    victim_ip = victim_ip or container_identity(victim)["ip"]
    deadline = time.monotonic() + timeout_seconds
    observations = []
    matching = 0
    while time.monotonic() < deadline:
        states = {node: membership(node) for node in nodes if node != victim}
        parsed = {node: parse_status(status) for node, status in states.items()}
        good = all(victim_ip in rows and rows[victim_ip]["state"] == "DN" and
                   sum(row["state"] == "UN" for row in rows.values()) == len(nodes) - 1
                   for rows in parsed.values())
        matching = matching + 1 if good else 0
        observations.append({"time_ns": time.time_ns(), "raw": states,
                             "parsed": parsed, "matching": good})
        if matching >= consecutive:
            return {"victim": victim, "victim_ip": victim_ip,
                    "required_consecutive": consecutive, "observations": observations}
        time.sleep(2)
    raise TimeoutError(f"survivors did not confirm {victim} down")


def restart_node(node):
    return compose("start", node)


def _rules_for(node, blocked, ips, ports=(7000, 7001)):
    rules = []
    for peer in blocked.get(node, ()):
        for flag in ("--dports", "--sports"):
            rules.append(["-d", ips[peer] + "/32", "-p", "tcp", "-m", "multiport", flag,
                          ",".join(str(port) for port in ports), "-j", "DROP"])
    return rules


def set_graph(blocked_edges, ports=(7000, 7001), nodes=None):
    nodes = _nodes(nodes)
    ips = {node: container_ip(node) for node in nodes}
    blocked = {node: [] for node in nodes}
    for left, right in blocked_edges:
        if left not in nodes or right not in nodes or left == right:
            raise ValueError((left, right))
        blocked[left].append(right)
        blocked[right].append(left)
    current = {}
    for node in nodes:
        node_exec(node, "iptables", "-N", "LAB_FAULT", check=False)
        output_rules = node_exec(node, "iptables", "-S", "OUTPUT", check=False)
        if "-A OUTPUT -j LAB_FAULT" not in output_rules:
            node_exec(node, "iptables", "-I", "OUTPUT", "1", "-j", "LAB_FAULT")
        current[node] = [shlex.split(line)[2:] for line in
                         node_exec(node, "iptables", "-S", "LAB_FAULT", check=False).splitlines()
                         if line.startswith("-A ")]
    desired = {node: _rules_for(node, blocked, ips, ports) for node in nodes}
    for node in nodes:
        for rule in desired[node]:
            if rule not in current[node]:
                node_exec(node, "iptables", "-A", "LAB_FAULT", *rule)
    for node in nodes:
        for rule in current[node]:
            if rule not in desired[node]:
                node_exec(node, "iptables", "-D", "LAB_FAULT", *rule)
    return {"ips": ips, "blocked": blocked,
            "rules": {node: node_exec(node, "iptables", "-S", "LAB_FAULT") for node in nodes},
            "counters": {node: node_exec(node, "iptables", "-L", "LAB_FAULT", "-v", "-n") for node in nodes}}


def set_partition(isolated, ports=(7000, 7001), nodes=None):
    nodes = _nodes(nodes)
    return set_graph([(isolated, node) for node in nodes if node != isolated], ports, nodes)


def clear_partition(nodes=None):
    # set_partition's empty graph is not usable because it needs all containers, so
    # remove only rules in the project chain and leave unrelated firewall state alone.
    for node in _nodes(nodes):
        rules = [shlex.split(line)[2:] for line in node_exec(node, "iptables", "-S", "LAB_FAULT", check=False).splitlines()
                 if line.startswith("-A ")]
        for rule in rules:
            node_exec(node, "iptables", "-D", "LAB_FAULT", *rule, check=False)
        node_exec(node, "iptables", "-D", "OUTPUT", "-j", "LAB_FAULT", check=False)


def partition_snapshot(nodes=None):
    return {node: {"rules": node_exec(node, "iptables", "-S", "LAB_FAULT", check=False),
                   "counters": node_exec(node, "iptables", "-L", "LAB_FAULT", "-v", "-n", check=False)}
            for node in _nodes(nodes)}


def recover_all(timeout_seconds=600, nodes=None):
    """Idempotently restart every lab node, remove lab rules, and verify membership."""
    nodes = _nodes(nodes)
    actions = []
    for node in nodes:
        actions.append({"node": node, "start": compose("start", node, check=False)})
    clear_partition(nodes)
    return {"actions": actions, "membership": wait_healthy(timeout_seconds, nodes),
            "completed_ns": time.time_ns()}
