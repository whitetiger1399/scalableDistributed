"""Single validated configuration contract for planning, execution and verification."""
from copy import deepcopy
import re

MODELS = ("RYW", "MR", "MW", "WFR")
SCENARIOS = ("normal", "node_failure", "network_partition")
EXPERIMENTS = ("session_guarantees", "node_failure", "network_partition",
               "read_repair", "timestamp_control")
CONSISTENCIES = {"ONE", "QUORUM", "ALL"}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
COMPOSE_FILE = re.compile(r"^compose(?:[._-][a-z0-9_-]+)?\.ya?ml$")
DEFAULT_CLUSTER = {
    "profile": "three_node",
    "compose_file": "compose.yaml",
    "nodes": ["n1", "n2", "n3"],
}


def _unique(name, values):
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} must be a non-empty list")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} contains duplicates")


def normalize(raw, full=True):
    config = deepcopy(raw)
    required = {"design", "routing", "repetitions", "rounds", "models", "consistency_configs",
                "scenarios", "enabled_experiments", "faults", "database"}
    missing = required - set(config)
    if missing:
        raise ValueError(f"missing configuration fields: {sorted(missing)}")
    if not isinstance(config["design"], str) or not IDENTIFIER.match(config["design"].replace("-", "_")):
        raise ValueError("design must be a safe identifier")
    if config.get("seed") is not None and (isinstance(config["seed"], bool) or
                                             not isinstance(config["seed"], int)):
        raise ValueError("seed must be null or an integer")
    cluster = config.setdefault("cluster", deepcopy(DEFAULT_CLUSTER))
    if not isinstance(cluster, dict):
        raise ValueError("cluster must be an object")
    if not isinstance(cluster.get("profile"), str) or not IDENTIFIER.match(
            cluster["profile"].replace("-", "_")):
        raise ValueError("cluster.profile must be a safe identifier")
    compose_file = cluster.get("compose_file")
    if not isinstance(compose_file, str) or not COMPOSE_FILE.match(compose_file):
        raise ValueError("cluster.compose_file must name a repository compose YAML file")
    nodes = cluster.get("nodes")
    _unique("cluster.nodes", nodes)
    if len(nodes) < 3 or any(not isinstance(node, str) or not IDENTIFIER.match(node)
                             for node in nodes):
        raise ValueError("cluster.nodes must contain at least three safe service names")
    routing = config["routing"]
    if routing != {"policy": "token_aware_dc_aware", "local_dc": "dc1"}:
        raise ValueError("routing must use token_aware_dc_aware in local_dc dc1")
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
        raise ValueError("these experiment profiles require replication_factor=3")
    if db["replication_factor"] > len(nodes):
        raise ValueError("replication_factor cannot exceed the Cassandra node count")
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
    faults.setdefault("post_recovery_settle_seconds", 0)
    faults.setdefault("node_failure_count", 1)
    if faults["node_failure_count"] != 1:
        raise ValueError("the current node-failure oracle supports node_failure_count=1")
    faults.setdefault("partition_strategy", "isolate_one")
    if faults["partition_strategy"] not in {"isolate_one", "balanced_random"}:
        raise ValueError("partition_strategy must be isolate_one or balanced_random")
    if faults["partition_strategy"] == "balanced_random":
        sizes = faults.get("partition_group_sizes")
        if (not isinstance(sizes, list) or len(sizes) != 2 or
                any(isinstance(size, bool) or not isinstance(size, int) or size < 1
                    for size in sizes) or sum(sizes) != len(nodes)):
            raise ValueError("balanced_random requires two positive partition_group_sizes summing to node count")
    else:
        faults.pop("partition_group_sizes", None)
    for field in ("failure_detection_timeout_seconds", "recovery_timeout_seconds",
                  "partition_stabilization_seconds", "partition_hold_seconds",
                  "post_recovery_settle_seconds"):
        value = faults.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValueError(f"{field} must be a non-negative number")
    if len(nodes) != 3 and "read_repair" in config["enabled_experiments"]:
        raise ValueError("read_repair control currently requires the three-node cluster profile")
    config["profile"] = "full" if full else "smoke"
    return config


def expected_main_trials(config):
    if "session_guarantees" not in config["enabled_experiments"]:
        return 0
    return (len(config["scenarios"]) * len(config["consistency_configs"])
            * len(config["models"]) * config["rounds"])
