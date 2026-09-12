import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from checks import classify

def ok(a=0,b=0):
    return {'status':'ok','value':{'a':a,'b':b}}

class HistoryChecks(unittest.TestCase):
    def test_stale_read(self):
        self.assertEqual(classify('RYW',[ok(1),ok(0)]),'violation')
    def test_regression(self):
        self.assertEqual(classify('MR',[ok(1),ok(1),ok(0)]),'violation')
    def test_dependency_witness(self):
        for model in ('MW','WFR'):
            self.assertEqual(classify(model,[ok(1),ok(0,1)]),'violation')
            self.assertEqual(classify(model,[ok(1),ok(1,1)]),'no_violation_observed')
    def test_absent_successor_is_inconclusive(self):
        self.assertEqual(classify('MW',[ok(1),ok(0,0)]),'inconclusive')
    def test_error_is_not_violation(self):
        for model in ('RYW','MR','MW','WFR'):
            self.assertEqual(classify(model,[{'status':'error'},ok()]),'inconclusive')

if __name__=='__main__':
    unittest.main()
