"""Registry of readable, model-specific client histories."""
from . import mr, mw, ryw, wfr

REGISTRY = {"RYW": ryw, "MR": mr, "MW": mw, "WFR": wfr}


def operations(model, key, write_cl, read_cl, timestamp, table="blocking"):
    try:
        module = REGISTRY[model]
    except KeyError:
        raise ValueError(f"unknown model: {model}")
    return module.operations(key, write_cl, read_cl, timestamp, table)
