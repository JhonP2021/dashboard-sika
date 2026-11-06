import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest import mock

import pandas as pd
from streamlit.testing.v1 import AppTest

from config import settings as settings_module
from src.models.data_cleaner import clean_m1
from src.models.material_normalizer import canonical_material, load_canonical_map, load_status_canonicals


class AccessTypesTests(unittest.TestCase):
    def test_access_time_values_keep_rows(self):
        # pyodbc entrega la hora de Access como 1899-12-30 + hora.
        raw = pd.DataFrame({
            "ReportDate": [datetime(2026, 6, 23), datetime(2026, 6, 23)],
            "ReportTime": [datetime(1899, 12, 30, 0, 4, 43), datetime(1899, 12, 30, 8, 15, 0)],
            "Recipe1Name": ["CERAM 130", "CERAM 130"],
            "NumberBatchDone1": [1, 2],
        })
        result = clean_m1(raw)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["report_datetime"].tolist(),
                         [pd.Timestamp("2026-06-23 00:04:43"), pd.Timestamp("2026-06-23 08:15:00")])


class SettingsTests(unittest.TestCase):
    def _settings(self, **env):
        settings_module.get_settings.cache_clear()
        with mock.patch.dict(os.environ, env, clear=True):
            try:
                return settings_module.get_settings()
            finally:
                settings_module.get_settings.cache_clear()

    def test_access_path_alone_selects_access(self):
        self.assertEqual(self._settings(ACCESS_DB_PATH=r"C:\datos\base.accdb").mode, "PROD")

    def test_without_access_path_uses_csv(self):
        self.assertEqual(self._settings().mode, "DEV")

    def test_bad_numbers_fall_back(self):
        with mock.patch.dict(os.environ, {"X": "2,5", "Y": "2%"}):
            self.assertEqual(settings_module.env_number("X", 1.0), 2.5)
            self.assertEqual(settings_module.env_number("Y", 1.0), 1.0)


class MaterialsMapTests(unittest.TestCase):
    def _write(self, text, encoding="utf-8"):
        handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding=encoding)
        handle.write(text)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return Path(handle.name)

    def test_excel_spanish_csv(self):
        path = self._write("familia;variante;canonico\nESTADO;VACÍO;VACÍO\nARENA;ARENA  #8;ARENA #8\n", "cp1252")
        self.assertEqual(load_status_canonicals(path), {"VACIO"})
        mapping = load_canonical_map(path)
        self.assertEqual(canonical_material("VACÍO", mapping), "VACIO")
        self.assertEqual(canonical_material("ARENA  #8", mapping), "ARENA #8")

    def test_empty_map_is_ignored(self):
        path = self._write("")
        self.assertEqual(load_canonical_map(path), {})
        self.assertEqual(load_status_canonicals(path), set())

    def test_lfs_pointer_is_ignored(self):
        path = self._write("version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 29626\n")
        self.assertEqual(load_canonical_map(path), {})
        self.assertEqual(load_status_canonicals(path), set())


SCRIPT = '''
from datetime import date
import streamlit as st
from src.components.sidebar import render_sidebar
render_sidebar(formula_options={}, available_operators=[], available_lots=[],
    min_date=date(2026,1,1), max_date=st.session_state.get("test_max", date(2026,6,24)), batch_bounds=None)
'''


class DateReanchorTests(unittest.TestCase):
    def test_default_range_follows_new_data(self):
        app = AppTest.from_string(SCRIPT).run()
        app.session_state["test_max"] = date(2026, 6, 25)
        app.run()
        self.assertEqual(app.session_state["dashboard_applied_dates"][1], date(2026, 6, 25))

    def test_custom_range_is_kept(self):
        app = AppTest.from_string(SCRIPT).run()
        app.date_input[0].set_value(date(2026, 6, 1))
        app.date_input[1].set_value(date(2026, 6, 10))
        app.button[1].click().run()
        app.session_state["test_max"] = date(2026, 6, 25)
        app.run()
        self.assertEqual(app.session_state["dashboard_applied_dates"], (date(2026, 6, 1), date(2026, 6, 10)))


if __name__ == "__main__":
    unittest.main()
