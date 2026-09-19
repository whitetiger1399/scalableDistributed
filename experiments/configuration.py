"""Single validated configuration contract for planning, execution and verification."""
from copy import deepcopy
import re

MODELS = ("RYW", "MR", "MW", "WFR")
SCENARIOS = ("normal", "node_failure", "network_partition")
EXPERIMENTS = ("session_guarantees", "node_failure", "network_partition",
               "read_repair", "timestamp_control")
CONSISTENCIES = {"ONE", "QUORUM", "ALL"}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def _unique(name, values):
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} must be a non-empty list")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} contains duplicates")


def normalize(raw, full=True):
    config = deepcopy(raw)
    required = {"design", "repetitions", "rounds", "models", "consistency_configs",
                "scenarios", "enabled_experiments", "faults", "database"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"missing configuration fields: {sorted(missing)}")
    if not isinstance(config["design"], str) or not IDENTIFIER.match(config["design"].replace("-", "_")):
        raise ValueError("design must be a safe identifier")
    if config.get("seed") is not None and (isinstance(config["seed"], bool) or
                                             not isinstance(config["seed"], int)):
        raise ValueError("seed must be null or an integer")
    for name in ("models", "consistency_configs", "scenarios", "enabled_experiments"):
        _unique(name, config[name])
    if set(config["models"]) - set(MODELS):
        raise ValueError("unknown model")
    if set(config["scenarios"]) - set(SCENARIOS):
        raise ValueError("unknown scenario")
    if set(config["enabled_experiments"]) - set(EXPERIMENTS):
        raise ValueError("unknown experiment type")
    for pair in config["consistency_configs"]:
        parts = pair.split("/")
        if len(parts) != 2 or any(part not in CONSISTENCIES for part in parts):
            raise ValueError(f"invalid write/read consistency pair: {pair}")
    for name in ("repetitions", "rounds"):
        if isinstance(config[name], bool) or not isinstance(config[name], int):
            raise ValueError(f"{name} must be an integer")
    if config["repetitions"] != config["rounds"]:
        raise ValueError("repetitions and rounds must match")
    if full and config["rounds"] < 10:
        raise ValueError("a full run requires at least 10 repetitions per case")
    if not full and config["rounds"] < 1:
        raise ValueError("a smoke run requires at least one repetition")
    if full and "session_guarantees" in config["enabled_experiments"] and set(config["models"]) != set(MODELS):
        raise ValueError("the submission profile must include RYW, MR, MW and WFR")
    for scenario, experiment in (("node_failure", "node_failure"),
                                 ("network_partition", "network_partition")):
        if scenario in config["scenarios"] and experiment not in config["enabled_experiments"]:
            raise ValueError(f"{scenario} scenario requires the {experiment} experiment")
    db = config["database"]
    if db.get("replication_factor") != 3:
        raise ValueError("this deployment supports replication_factor=3 only")
    if db.get("hints_enabled") is not False:
        raise ValueError("this image supports hints_enabled=false only")
    tables = db.get("read_repair_tables")
    if tables != {"blocking": "BLOCKING", "no_repair": "NONE"}:
        raise ValueError("read_repair_tables must match the deployed schema")
    faults = config["faults"]
    if faults.get("cql_port") != 9042:
        raise ValueError("this deployment supports cql_port=9042 only")
    ports = faults.get("internode_ports")
    if not isinstance(ports, list) or not ports or any(not isinstance(p, int) for p in ports):
        raise ValueError("internode_ports must be a non-empty integer list")
    for field in ("failure_detection_timeout_seconds", "recovery_timeout_seconds",
                  "partition_stabilization_seconds", "partition_hold_seconds"):
        value = faults.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{field} must be a non-negative number")
    config["profile"] = "full" if full else "smoke"
    return config


def expected_main_trials(config):
    if "session_guarantees" not in config["enabled_experiments"]:
        return 0
    return (len(config["scenarios"]) * len(config["consistency_configs"])
            * len(config["models"]) * config["rounds"])
