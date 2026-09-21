"""Main four-model driver-routed session-guarantee experiment."""
from .common import cases, expected_main_trials


def build_round(config, run_id, round_no, scenario, rng):
    return cases(config, run_id, round_no, scenario, rng)


def expected_trials(config):
    return expected_main_trials(config)


def description():
    return "For every model/configuration/scenario case, Cassandra's token-aware, DC-aware driver policy selects each operation's coordinator."
