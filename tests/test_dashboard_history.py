import unittest

import pandas as pd

from src.components.charts import SILO_PLOT_BLOCKS, plot_silo_differences
from src.models.data_cleaner import clean_m1
from src.models.data_merger import material_long, operator_long


class HistoryTests(unittest.TestCase):
    def test_large_plot_preserves_extremes_and_counts_with_bounded_points(self):
        count = 10001
        data = pd.DataFrame({'report_datetime': pd.date_range('2020-01-01', periods=count, freq='min'),
                             'Silo 1_pct': [0.] * count})
        data.loc[0, 'Silo 1_pct'] = -900
        data.loc[count - 1, 'Silo 1_pct'] = 1200
        trace = plot_silo_differences(data, percentage=True).data[0]
        self.assertLessEqual(len(trace.x), SILO_PLOT_BLOCKS)
        self.assertEqual(sum(row[1] for row in trace.customdata), count)
        self.assertEqual(min(row[2] for row in trace.customdata), -900)
        self.assertEqual(max(row[3] for row in trace.customdata), 1200)

    def test_invalid_dates_and_unused_silos(self):
        data = pd.DataFrame({
            'ReportDate': ['2020-01-01', None, '2026-01-01'],
            'ReportTime': ['12:00:00'] * 3, 'NumberBatchDone1': [1, 2, 3],
            'OperatorName': ['A'] * 3, 'Silo1Des': ['CEMENTO'] * 3,
            'Silo1Target': [0, 10, 10], 'Silo1Real': [0, 10, 11],
            'Differentiel_Silo_1': [0, 0, 1], 'Differentiel_Silo_1_PC': [0, 0, 10],
        })
        cleaned = clean_m1(data, materials={})
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned["Silo 1_pct"].tolist(), [0, 10])
        self.assertEqual(cleaned["Silo 1_kg"].tolist(), [0, 1])
        self.assertAlmostEqual(cleaned["Silo 1_pct"].std(), pd.Series([0, 10]).std())
        self.assertEqual(cleaned.report_day.min().year, 2020)
        self.assertEqual(len(material_long(cleaned)), 1)
        self.assertEqual(len(operator_long(cleaned)), 1)
        self.assertEqual(len(clean_m1(data, min_year=2026)), 1)


if __name__ == '__main__':
    unittest.main()
