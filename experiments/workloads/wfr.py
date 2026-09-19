"""Writes-follow-reads observable with producer, dependent client and observer."""


def operations(key, write_cl, read_cl, timestamp, table):
    return [
        {"kind": "write", "key": key, "column": "a", "value": 1, "ts": timestamp,
         "cl": write_cl, "table": table, "role": "producer", "client_id": "producer-1"},
        {"kind": "read", "key": key, "cl": read_cl, "table": table,
         "role": "dependent", "client_id": "client-1"},
        {"kind": "write", "key": key, "column": "b", "value": 1, "ts": timestamp + 1,
         "cl": write_cl, "table": table, "role": "dependent", "client_id": "client-1"},
        {"kind": "read", "key": key, "cl": read_cl, "table": table,
         "role": "observer", "client_id": "observer-1"},
    ]
