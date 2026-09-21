"""Explicit timestamp-order control workload."""


def expected_trials(config):
    if "timestamp_control" not in config.get("enabled_experiments", ["timestamp_control"]):
        return 0
    return config["rounds"]


def description():
    return "Use driver-selected coordinators for ALL write(a=1,T+100), ALL write(a=2,T+50), and ALL read(a), repeated once per round."


def operations(key, timestamp, table="blocking"):
    return [
        {"kind": "write", "key": key, "column": "a", "value": 1,
         "ts": timestamp + 100, "cl": "ALL", "table": table,
         "role": "client", "client_id": "client-1"},
        {"kind": "write", "key": key, "column": "a", "value": 2,
         "ts": timestamp + 50, "cl": "ALL", "table": table,
         "role": "client", "client_id": "client-1"},
        {"kind": "read", "key": key, "cl": "ALL", "table": table,
         "role": "client", "client_id": "client-1"},
    ]
