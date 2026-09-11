import unittest
import pandas as pd
from src.models.silo_metrics import silo_incidents


class SiloMetricsTests(unittest.TestCase):
    def test_one_extreme_does_not_classify_whole_silo(self):
        df = pd.DataFrame({'Silo1Target': [100]*1000, 'Silo1Real': [100]*999+[120],
                           'Silo 1_pct': [0]*999+[20]})
        original = df.copy(deep=True)
        result = silo_incidents(df, 1)
        self.assertEqual(result['extreme'], 1)
        self.assertEqual(result['outside'], 1)
        self.assertEqual(result['compliance_pct'], 99.9)
        pd.testing.assert_frame_equal(df, original)

    def test_boundaries_and_data_quality(self):
        df = pd.DataFrame({'Silo1Target': [100,100,100,100,0,0,100,100,100],
                           'Silo1Real': [105,110,111,0,0,20,None,100,100],
                           'Silo 1_pct': [5,10,11,-100,0,0,0,float('inf'),None]})
        r = silo_incidents(df, 1)
        self.assertEqual(r['evaluated'], 4)
        self.assertEqual(r['outside'], 3)
        self.assertEqual(r['extreme'], 2)
        self.assertEqual(r['zero_real'], 1)
        self.assertEqual(r['extreme_zero_real'], 1)
        self.assertEqual(r['no_target'], 1)
        self.assertEqual(r['invalid'], 3)
        self.assertEqual(r['compliance_pct'], 25)

    def test_empty_and_material_scope(self):
        self.assertIsNone(silo_incidents(pd.DataFrame(),1)['compliance_pct'])
        df = pd.DataFrame({'Silo1Target':[100,100],'Silo1Real':[100,0],
                           'Silo 1_pct':[0,-100],'Silo 1_material':['A','B']})
        r=silo_incidents(df,1,materials=['A'])
        self.assertEqual(r['compliance_pct'],100)
        self.assertEqual(r['zero_real'],0)

if __name__ == '__main__':
    unittest.main()
