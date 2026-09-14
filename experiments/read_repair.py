"""Focused BLOCKING versus NONE read-repair workload."""


def settings(config):
    return list(config["database"]["read_repair_tables"].items())


def expected_trials(config):
    if "read_repair" not in config.get("enabled_experiments", ["read_repair"]):
        return 0
    return len(settings(config)) * config["rounds"]


def description():
    return "Create a minority-only value, change between two-node quorum components without a fully connected interval, and compare successive random-coordinator QUORUM reads."
