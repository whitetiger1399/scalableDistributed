import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
sys.path.insert(0, str(ROOT/'src'))
from checks import evaluate
from verify_randomized import EvidenceError, verify


def operation(kind, key, sequence, cl, start, value=None):
    record = {"kind":kind, "sequence":sequence, "status":"ok", "cl":cl,
              "params":[key], "start_ns":start, "end_ns":start+1,
              "node":"n1", "coordinator":"127.0.0.1:9042", "client_id":"client-1",
              "routing_key":key,
              "routing":{"policy":"TokenAwarePolicy(DCAwareRoundRobinPolicy)",
                         "local_dc":"dc1", "selected_node":"n1",
                         "eligible_nodes":["n1","n2","n3"],
                         "attempted_nodes":["n1"], "operation_index":sequence}}
    if kind == 'read':
        record['value'] = value
    return record


class VerifierTests(unittest.TestCase):
    def make_run(self):
        temp = tempfile.TemporaryDirectory()
        run = Path(temp.name)
        base = json.loads((ROOT/'config/cassandra_driver_experiments.json').read_text())
        base.update(models=['RYW'], consistency_configs=['ONE/ONE'], scenarios=['normal'],
                    enabled_experiments=['session_guarantees'], rounds=1, repetitions=1,
                    profile='smoke')
        key='design:run:normal:0:ONE/ONE:RYW'
        ops=[operation('write',key,0,'ONE',1),operation('read',key,1,'ONE',3,{'a':1,'b':0})]
        result=evaluate('RYW',ops)
        trial={"trial_id":"run:normal:0:ONE/ONE:RYW", "scenario":"normal", "round":0,
               "config":"ONE/ONE", "model":"RYW", "key":key, "attempt":1,
               "episode_id":"main:normal:0", "operations":ops, **result}
        init={"records":[{"status":"ok","cl":"ALL","params":[key]}]}
        episode={"episode_id":"main:normal:0", "scenario":"normal", "round":0,
                 "schedule":[{"key":key}], "initialization":init, "trials":[trial],
                 "fault":None, "recovery":None}
        files={
            'plan.json':base,
            'completion.json':{"completed":True,"evidence_schema":"cassandra-driver-policy-evidence-v4",
                               "run_id":"run","main_trials":1,"read_repair_trials":0,"timestamp_trials":0},
            'environment.json':{"evidence_schema":"cassandra-driver-policy-evidence-v4","run_id":"run"},
            'trials.json':[trial], 'faults.json':[episode],
            'read_repair.json':[], 'timestamp_control.json':[]}
        for name,value in files.items():
            (run/name).write_text(json.dumps(value))
        return temp,run

    def test_valid_smoke_fixture_returns_json_safe_cases(self):
        temp,run=self.make_run()
        try:
            result=verify(run)
            json.dumps(result)
            self.assertEqual(result['cases'][0]['attempts'],1)
        finally:
            temp.cleanup()

    def test_changed_verdict_is_rejected(self):
        temp,run=self.make_run()
        try:
            trials=json.loads((run/'trials.json').read_text())
            trials[0]['verdict']='violation'
            (run/'trials.json').write_text(json.dumps(trials))
            with self.assertRaisesRegex(EvidenceError,'recomputed'):
                verify(run)
        finally:
            temp.cleanup()


if __name__ == '__main__':
    unittest.main()
