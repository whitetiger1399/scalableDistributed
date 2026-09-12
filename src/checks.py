"""Finite-history counterexamples; errors and unmet prerequisites are separate."""

def classify(model, operations):
    if model not in ('RYW','MR','MW','WFR'):
        raise ValueError(model)
    if any(op['status'] != 'ok' for op in operations):
        return 'inconclusive'
    if model == 'WFR' and operations[1]['value']['a'] != 1:
        return 'inconclusive'
    if model == 'RYW':
        violation = operations[-1]['value']['a'] < 1
    elif model == 'MR':
        violation = operations[-1]['value']['a'] < operations[-2]['value']['a']
    else:
        value = operations[-1]['value']
        if value['b'] != 1:
            return 'inconclusive'
        violation = value['a'] != 1
    return 'violation' if violation else 'no_violation_observed'


def inconclusive_reason(model, operations):
    if any(op['status'] != 'ok' for op in operations):
        return 'operation_error'
    if model=='WFR' and operations[1]['value']['a']!=1:
        return 'dependency_not_observed'
    if model in ('MW','WFR') and operations[-1]['value']['b']!=1:
        return 'successor_not_observed'
    return None
