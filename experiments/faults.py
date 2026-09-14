"""Project-scoped Docker/Cassandra fault injection and recovery helpers."""
import json
import os
import shlex
import subprocess
import time

NODES = ("n1", "n2", "n3")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def command(args, data=None, check=True):
    result = subprocess.run(args, input=data, text=True, capture_output=True)
    if check and result.returncode:
        raise RuntimeError(f"{shlex.join(args)}\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def compose(*args, data=None, check=True):
    executable = os.environ.get("COMPOSE_BIN")
    base = [executable] if executable else ["docker", "compose"]
    return command(base + ["-f", os.path.join(ROOT, "compose.yaml")] + list(args), data=data, check=check)


def node_exec(node, *args, check=True):
    return compose("exec", "-T", "-u", "root", node, *args, check=check)


def container_ip(node):
    cid = compose("ps", "-q", node)
    info = json.loads(command(["docker", "inspect", cid]))[0]
    return next(iter(info["NetworkSettings"]["Networks"].values()))["IPAddress"]


def membership(observer="n1"):
    return node_exec(observer, "nodetool", "status", check=False)


def all_healthy():
    states = {node: membership(node) for node in NODES}
    return all(sum(line.startswith("UN ") for line in value.splitlines()) == 3
               for value in states.values())


def wait_healthy(timeout_seconds=600):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if all_healthy():
            return {node: membership(node) for node in NODES}
        time.sleep(5)
    raise TimeoutError("cluster did not return to three UN nodes")


def kill_node(node):
    started = time.time_ns()
    output = compose("kill", "-s", "SIGKILL", node)
    return {"action": "docker compose kill -s SIGKILL " + node,
            "node": node, "start_ns": started, "output": output}


def wait_failure(victim, timeout_seconds=90):
    deadline = time.monotonic() + timeout_seconds
    observations = []
    while time.monotonic() < deadline:
        states = {node: membership(node) for node in NODES if node != victim}
        observations.append(states)
        if all(sum(line.startswith("UN ") for line in status.splitlines()) == 2 and
               any(victim in line and line.startswith("DN ") for line in status.splitlines())
               for status in states.values()):
            return observations
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


def set_graph(blocked_edges, ports=(7000, 7001)):
    ips = {node: container_ip(node) for node in NODES}
    blocked = {node: [] for node in NODES}
    for left, right in blocked_edges:
        if left not in NODES or right not in NODES or left == right:
            raise ValueError((left, right))
        blocked[left].append(right)
        blocked[right].append(left)
    current = {}
    for node in NODES:
        node_exec(node, "iptables", "-N", "LAB_FAULT", check=False)
        output_rules = node_exec(node, "iptables", "-S", "OUTPUT", check=False)
        if "-A OUTPUT -j LAB_FAULT" not in output_rules:
            node_exec(node, "iptables", "-I", "OUTPUT", "1", "-j", "LAB_FAULT")
        current[node] = [shlex.split(line)[2:] for line in
                         node_exec(node, "iptables", "-S", "LAB_FAULT", check=False).splitlines()
                         if line.startswith("-A ")]
    desired = {node: _rules_for(node, blocked, ips, ports) for node in NODES}
    for node in NODES:
        for rule in desired[node]:
            if rule not in current[node]:
                node_exec(node, "iptables", "-A", "LAB_FAULT", *rule)
    for node in NODES:
        for rule in current[node]:
            if rule not in desired[node]:
                node_exec(node, "iptables", "-D", "LAB_FAULT", *rule)
    return {"ips": ips, "blocked": blocked,
            "rules": {node: node_exec(node, "iptables", "-S", "LAB_FAULT") for node in NODES},
            "counters": {node: node_exec(node, "iptables", "-L", "LAB_FAULT", "-v", "-n") for node in NODES}}


def set_partition(isolated, ports=(7000, 7001)):
    return set_graph([(isolated, node) for node in NODES if node != isolated], ports)


def clear_partition():
    # set_partition's empty graph is not usable because it needs all containers, so
    # remove only rules in the project chain and leave unrelated firewall state alone.
    for node in NODES:
        rules = [shlex.split(line)[2:] for line in node_exec(node, "iptables", "-S", "LAB_FAULT", check=False).splitlines()
                 if line.startswith("-A ")]
        for rule in rules:
            node_exec(node, "iptables", "-D", "LAB_FAULT", *rule, check=False)
        node_exec(node, "iptables", "-D", "OUTPUT", "-j", "LAB_FAULT", check=False)
