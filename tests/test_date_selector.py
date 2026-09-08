import unittest
from datetime import date
from streamlit.testing.v1 import AppTest

SCRIPT = '''
from datetime import date
import streamlit as st
from src.components.sidebar import render_sidebar
filters = render_sidebar(formula_options={}, available_operators=[], available_lots=[],
    min_date=date(2019,11,28), max_date=date(2026,6,24), batch_bounds=None)
st.text(str(filters.date_range))
'''


class DateSelectorTests(unittest.TestCase):
    def test_apply_validate_and_full_history(self):
        app = AppTest.from_string(SCRIPT).run()
        initial = app.session_state['dashboard_applied_dates']
        app.date_input[0].set_value(date(2026,6,1))
        app.date_input[1].set_value(date(2026,6,1))
        app.button[1].click().run()
        self.assertEqual(app.session_state['dashboard_applied_dates'], (date(2026,6,1),)*2)
        app.date_input[0].set_value(date(2026,6,20))
        app.button[1].click().run()
        self.assertEqual(len(app.error), 1)
        self.assertEqual(app.session_state['dashboard_applied_dates'], (date(2026,6,1),)*2)
        app.date_input[0].set_value(None)
        app.button[1].click().run()
        self.assertEqual(len(app.error), 1)
        self.assertEqual(app.session_state['dashboard_applied_dates'], (date(2026,6,1),)*2)
        app.button[0].click().run()
        self.assertEqual(app.session_state['dashboard_applied_dates'], (date(2019,11,28),date(2026,6,24)))
        self.assertEqual(app.date_input[0].value, date(2019,11,28))
        self.assertEqual(app.date_input[1].value, date(2026,6,24))
        self.assertFalse(app.exception)

if __name__ == '__main__':
    unittest.main()
