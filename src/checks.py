"""Robust finite-history oracles for the project's observable predicates."""

EXPECTED_LENGTH = {"RYW": 2, "MR": 3, "MW": 3, "WFR": 4}


def _read_cell(operation, column):
    value = operation.get("value")
    if value is None:
        return "missing", None
    if not isinstance(value, dict) or column not in value:
        return "malformed", None
    cell = value[column]
    return ("missing", None) if cell is None else ("value", cell)


def evaluate(model, operations):
    if model not in EXPECTED_LENGTH:
        raise ValueError(model)
    coverage = {"evaluable": False, "mr_first_read_exposed": False,
                "dependency_exposed": False, "successor_exposed": False}
    if not isinstance(operations, list) or len(operations) != EXPECTED_LENGTH[model]:
        return {"verdict": "inconclusive", "reason": "malformed_history", "coverage": coverage}
    if any(not isinstance(op, dict) or op.get("status") not in {"ok", "error"} for op in operations):
        return {"verdict": "inconclusive", "reason": "malformed_history", "coverage": coverage}
    if any(op["status"] != "ok" for op in operations):
        return {"verdict": "inconclusive", "reason": "operation_error", "coverage": coverage}

    if model == "RYW":
        state, value = _read_cell(operations[1], "a")
        if state == "malformed":
            return {"verdict": "inconclusive", "reason": "malformed_read", "coverage": coverage}
        coverage["evaluable"] = True
        violation = state == "missing" or value != 1
    elif model == "MR":
        first_state, first = _read_cell(operations[1], "a")
        second_state, second = _read_cell(operations[2], "a")
        if "malformed" in (first_state, second_state):
            return {"verdict": "inconclusive", "reason": "malformed_read", "coverage": coverage}
        first_version = -1 if first_state == "missing" else first
        second_version = -1 if second_state == "missing" else second
        coverage["mr_first_read_exposed"] = first == 1
        coverage["evaluable"] = True
        violation = second_version < first_version
    else:
        if model == "WFR":
            state, dependency = _read_cell(operations[1], "a")
            if state == "malformed":
                return {"verdict": "inconclusive", "reason": "malformed_read", "coverage": coverage}
            coverage["dependency_exposed"] = dependency == 1
            if dependency != 1:
                return {"verdict": "inconclusive", "reason": "dependency_not_observed",
                        "coverage": coverage}
        final_state_a, predecessor = _read_cell(operations[-1], "a")
        final_state_b, successor = _read_cell(operations[-1], "b")
        if "malformed" in (final_state_a, final_state_b):
            return {"verdict": "inconclusive", "reason": "malformed_read", "coverage": coverage}
        coverage["successor_exposed"] = successor == 1
        if successor != 1:
            return {"verdict": "inconclusive", "reason": "successor_not_observed",
                    "coverage": coverage}
        coverage["evaluable"] = True
        violation = predecessor != 1
    return {"verdict": "violation" if violation else "no_violation_observed",
            "reason": None, "coverage": coverage}


def classify(model, operations):
    return evaluate(model, operations)["verdict"]


def inconclusive_reason(model, operations):
    return evaluate(model, operations)["reason"]
