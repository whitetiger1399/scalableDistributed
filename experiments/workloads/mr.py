"""Monotonic reads: a producer writes, then one client performs two reads."""


def operations(key, write_cl, read_cl, timestamp, table):
    return [
        {"kind": "write", "key": key, "column": "a", "value": 1, "ts": timestamp,
         "cl": write_cl, "table": table, "role": "producer", "client_id": "producer-1"},
        {"kind": "read", "key": key, "cl": read_cl, "table": table,
         "role": "client", "client_id": "client-1"},
        {"kind": "read", "key": key, "cl": read_cl, "table": table,
         "role": "client", "client_id": "client-1"},
    ]
