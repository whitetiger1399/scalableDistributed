"""Focused BLOCKING versus NONE read-repair workload."""


def settings(config):
    return list(config["database"]["read_repair_tables"].items())


def expected_trials(config):
    if "read_repair" not in config.get("enabled_experiments", ["read_repair"]):
        return 0
    return len(settings(config)) * config["rounds"]


def description():
    return "Create a minority-only value, change between two-node quorum components without a fully connected interval, and compare successive random-coordinator QUORUM reads."


def minority_write(key, timestamp, table):
    return {"kind": "write", "key": key, "column": "a", "value": 1,
            "ts": timestamp, "cl": "ONE", "table": table,
            "role": "producer", "client_id": "producer-1"}


def quorum_read(key, table):
    return {"kind": "read", "key": key, "cl": "QUORUM", "table": table,
            "role": "client", "client_id": "client-1"}


def topology_pairs(write_coordinator, nodes, rng):
    others = [node for node in nodes if node != write_coordinator]
    rng.shuffle(others)
    return (write_coordinator, others[0]), (others[0], others[1])
