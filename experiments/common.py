"""Shared case construction; no Cassandra or Docker calls belong here."""
from .configuration import expected_main_trials


def cases(config, run_id, round_no, scenario, rng):
    """Return a randomized block containing one case per model/configuration."""
    rows = []
    for config_name in config["consistency_configs"]:
        for model in config["models"]:
            rows.append({
                "scenario": scenario,
                "round": round_no,
                "config": config_name,
                "model": model,
                "trial_id": f"{run_id}:{scenario}:{round_no}:{config_name}:{model}",
                "attempt": 1,
                "key": f"{config['design']}:{run_id}:{scenario}:r{round_no}:{config_name}:{model}",
            })
    rng.shuffle(rows)
    return rows


def expected_trials_by_case(config):
    return config["rounds"]
