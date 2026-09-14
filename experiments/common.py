"""Shared case construction; no Cassandra or Docker calls belong here."""
import random

MODELS = ("RYW", "MR", "MW", "WFR")


def cases(config, round_no, scenario, rng):
    """Return a randomized block containing one case per model/configuration."""
    rows = []
    for config_name in config["consistency_configs"]:
        for model in config["models"]:
            rows.append({
                "scenario": scenario,
                "round": round_no,
                "config": config_name,
                "model": model,
                "key": f"{config['design']}:{scenario}:r{round_no}:{config_name}:{model}",
            })
    rng.shuffle(rows)
    return rows


def expected_main_trials(config):
    if "session_guarantees" not in config.get("enabled_experiments", ["session_guarantees"]):
        return 0
    return (len(config["scenarios"]) * len(config["consistency_configs"])
            * len(config["models"]) * config["rounds"])


def expected_trials_by_case(config):
    return config["rounds"]
