import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from checks import classify, evaluate

def ok(a=0,b=0):
    return {'status':'ok','value':{'a':a,'b':b}}

class HistoryChecks(unittest.TestCase):
    def test_stale_read(self):
        self.assertEqual(classify('RYW',[ok(1),ok(0)]),'violation')
    def test_regression(self):
        self.assertEqual(classify('MR',[ok(1),ok(1),ok(0)]),'violation')
    def test_dependency_witness(self):
        self.assertEqual(classify('MW',[ok(1),ok(0,1),ok(0,1)]),'violation')
        self.assertEqual(classify('MW',[ok(1),ok(0,1),ok(1,1)]),'no_violation_observed')
        self.assertEqual(classify('WFR',[ok(1),ok(1),ok(0,1),ok(0,1)]),'violation')
        self.assertEqual(classify('WFR',[ok(1),ok(1),ok(1,1),ok(1,1)]),'no_violation_observed')
    def test_absent_successor_is_inconclusive(self):
        self.assertEqual(classify('MW',[ok(1),ok(0,1),ok(0,0)]),'inconclusive')
    def test_error_is_not_violation(self):
        examples = {'RYW':[{'status':'error'},ok()], 'MR':[{'status':'error'},ok(),ok()],
                    'MW':[{'status':'error'},ok(),ok()],
                    'WFR':[{'status':'error'},ok(),ok(),ok()]}
        for model, history in examples.items():
            self.assertEqual(classify(model,history),'inconclusive')

    def test_missing_and_malformed_reads_are_safe(self):
        self.assertEqual(classify('RYW',[ok(1),{'status':'ok','value':None}]),'violation')
        result=evaluate('MR',[ok(1),ok(1),{'status':'ok','value':None}])
        self.assertEqual(result['verdict'],'violation')
        result=evaluate('RYW',[ok(1),{'status':'ok','value':{'b':0}}])
        self.assertEqual((result['verdict'],result['reason']),('inconclusive','malformed_read'))

if __name__=='__main__':
    unittest.main()
