"""Explicit timestamp-order control workload."""


def expected_trials(config):
    if "timestamp_control" not in config.get("enabled_experiments", ["timestamp_control"]):
        return 0
    return config["rounds"]


def description():
    return "Use random coordinators for ALL write(a=1,T+100), ALL write(a=2,T+50), and ALL read(a), repeated once per round."
