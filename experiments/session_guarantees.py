"""Main four-model randomized session-guarantee experiment."""
from .common import cases, expected_main_trials


def build_round(config, run_id, round_no, scenario, rng):
    return cases(config, run_id, round_no, scenario, rng)


def expected_trials(config):
    return expected_main_trials(config)


def description():
    return "For every model/configuration/scenario case, every operation is routed independently by the customer-facing random gateway."
