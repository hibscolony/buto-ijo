"""Streamlit behavior tests; real prediction checks are explicitly opt-in.

All seeded dashboard probabilities come from the actual local checkpoint. Empty
state and error-state tests do not construct a model or fabricate predictions.
"""

from contextlib import ExitStack
from copy import deepcopy
from html import escape
import os
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "app.py"


def _quick_page():
    from pages.quick_test import render

    render()


def _document_page():
    from pages.document_analysis import render

    render()


def _document_results():
    from pages.document_analysis import render_results

    render_results()


def _history_page():
    from pages.history import render

    render()


def _about_page():
    from pages.about_model import render

    render()


def _assert_clean(testcase, app):
    testcase.assertEqual(len(app.exception), 0, [item.value for item in app.exception])
    testcase.assertEqual(len(app.error), 0, [item.value for item in app.error])


def _table_html(app):
    return next((item.value for item in app.markdown if '<table class="claim-table">' in item.value), "")


def _navigate(app, label):
    """Follow an actual registered link for callable Streamlit pages.

    Streamlit 1.55 AppTest.switch_page only supports script-file pages. The page
    hash below comes from the app's emitted PageLink, matching browser navigation.
    """
    link = next(link for link in app.get("page_link") if link.proto.label == label)
    app._page_hash = link.proto.page_script_hash
    return app.run()


class EmptyStateUITests(unittest.TestCase):
    def test_home_loads_without_inference_and_has_expected_navigation(self):
        with patch("core.inference.predict_batch", side_effect=AssertionError("Unrequested inference")) as inference:
            app = AppTest.from_file(APP_FILE, default_timeout=30).run()
        _assert_clean(self, app)
        inference.assert_not_called()
        self.assertFalse(app.session_state["analysis_results"])
        self.assertTrue(any("BUTO IJO" in item.value for item in app.markdown))
        page_links = app.get("page_link")
        labels = [link.proto.label for link in page_links]
        for label in ("Beranda", "Analisis Dokumen", "Uji Teks Cepat", "Riwayat", "Tentang Model"):
            self.assertIn(label, labels)

    def test_document_page_does_not_analyze_before_button_is_pressed(self):
        with patch("pages.document_analysis.analyze_document", side_effect=AssertionError("Unrequested inference")) as inference:
            app = AppTest.from_function(_document_page, default_timeout=30).run()
        _assert_clean(self, app)
        inference.assert_not_called()
        self.assertTrue(app.button(key="analyze_document").disabled)
        self.assertEqual([item.label for item in app.tabs], ["Upload Dokumen", "Input Teks"])

    def test_quick_empty_input_shows_warning_without_loading_model(self):
        with patch("pages.quick_test.load_model", side_effect=AssertionError("Unrequested model load")) as loader:
            app = AppTest.from_function(_quick_page, default_timeout=30).run()
            app.button(key="analyze_quick").click().run()
        _assert_clean(self, app)
        loader.assert_not_called()
        self.assertTrue(any("Masukkan klaim" in item.value for item in app.warning))

    def test_invalid_model_path_is_reported_without_crashing(self):
        invalid = str(APP_FILE.parent / "tests" / "nonexistent-model-checkpoint-for-ui-test")
        with patch.dict(os.environ, {"BUTO_IJO_MODEL_PATH": invalid}):
            app = AppTest.from_function(_quick_page, default_timeout=30).run()
            app.text_area(key="quick_text_widget").set_value(
                "Kami berkomitmen menurunkan emisi karbon perusahaan."
            ).run()
            app.button(key="analyze_quick").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any("Folder model tidak ditemukan" in item.value for item in app.error))

    def test_history_has_an_empty_state(self):
        app = AppTest.from_function(_history_page, default_timeout=30).run()
        _assert_clean(self, app)
        self.assertTrue(any("Riwayat" in item.value or "riwayat" in item.value for item in app.markdown))

    def test_navigation_opens_each_page_without_running_inference(self):
        with patch("core.inference.predict_batch", side_effect=AssertionError("Unrequested inference")) as inference:
            app = AppTest.from_file(APP_FILE, default_timeout=30).run()
            for title in ("Analisis Dokumen", "Uji Teks Cepat", "Riwayat", "Tentang Model"):
                with self.subTest(page=title):
                    _navigate(app, title)
                    _assert_clean(self, app)
                    self.assertEqual(app.title[0].value, title)
            _navigate(app, "Beranda")
            _assert_clean(self, app)
        inference.assert_not_called()


@unittest.skipUnless(
    os.getenv("BUTO_IJO_RUN_MODEL_TESTS") == "1",
    "Set BUTO_IJO_RUN_MODEL_TESTS=1 for UI tests with actual model probabilities.",
)
class RealPredictionUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.inference import predict_batch
        from core.model import load_model
        from core.risk import calculate_document_risk
        from core.settings import get_settings

        cls.settings = get_settings()
        cls.bundle = load_model(cls.settings.model_path)
        cls.claims = [
            {"claim_id": 1, "page": 9, "text": "Kami berkomitmen menjaga lingkungan untuk masa depan yang lebih hijau."},
            {"claim_id": 2, "page": 3, "text": "Emisi gas rumah kaca turun 12,5% pada 2024 dibandingkan tahun dasar 2020."},
            {"claim_id": 3, "page": 7, "text": "Penggunaan energi terbarukan meningkat menjadi 30% dari total konsumsi energi."},
        ]
        cls.results = predict_batch(cls.claims, bundle=cls.bundle, settings=cls.settings)
        cls.summary = calculate_document_risk(cls.results)

    def _seed_document(self, app):
        app.session_state["analysis_results"] = deepcopy(self.results)
        app.session_state["original_probabilities"] = deepcopy(self.results)
        app.session_state["risk_summary"] = deepcopy(self.summary)
        app.session_state["document_metadata"] = {
            "name": "integration-test-report.pdf", "type": "PDF", "size": 1000,
            "page_count": 9, "signature": "ui-test-real-indobert",
        }
        app.session_state["truncated_claims"] = 0

    def test_quick_text_requires_explicit_button_and_retains_result_on_edit(self):
        from core.inference import predict_text

        text = self.claims[0]["text"]
        expected = predict_text(text, bundle=self.bundle, settings=self.settings)
        app = AppTest.from_function(_quick_page, default_timeout=30).run()
        with patch("pages.quick_test.predict_text", side_effect=AssertionError("Unrequested inference")) as inference:
            app.text_area(key="quick_text_widget").set_value(text).run()
        _assert_clean(self, app)
        inference.assert_not_called()
        app.button(key="analyze_quick").click().run()
        _assert_clean(self, app)
        actual = app.session_state["quick_result"]
        self.assertAlmostEqual(actual["greenwashing_probability"], expected["greenwashing_probability"], delta=1e-5)
        self.assertEqual(actual["prediction"], expected["prediction"])
        self.assertEqual(len(app.metric), 2)
        with patch("pages.quick_test.predict_text", side_effect=AssertionError("Unrequested inference")) as inference:
            app.text_area(key="quick_text_widget").set_value(text + " Klaim tambahan.").run()
        _assert_clean(self, app)
        inference.assert_not_called()
        self.assertEqual(app.session_state["quick_result"], actual)
        self.assertTrue(any("input sebelumnya" in item.value for item in app.info))

    def test_threshold_filter_search_sort_and_rerun_keep_original_probabilities(self):
        app = AppTest.from_function(_document_results, default_timeout=30)
        self._seed_document(app)
        patched_targets = (
            "pages.document_analysis.analyze_document",
            "pages.document_analysis.load_model",
            "pages.quick_test.predict_text",
            "core.inference.predict_batch",
        )
        with ExitStack() as context:
            forbidden = [context.enter_context(patch(target, side_effect=AssertionError("Unexpected inference or load"))) for target in patched_targets]
            app.run()
            _assert_clean(self, app)
            self.assertEqual(len(app.get("download_button")), 2)

            expected_order = [str(row["claim_id"]) for row in sorted(self.results, key=lambda row: row["greenwashing_probability"], reverse=True)]
            self.assertEqual(re.findall(r"<tr><td>(\d+)</td>", _table_html(app)), expected_order)

            app.selectbox(key="claim_sort").set_value("Page").run()
            _assert_clean(self, app)
            self.assertEqual(re.findall(r"<tr><td>(\d+)</td>", _table_html(app)), ["2", "3", "1"])

            app.text_input(key="claim_search").set_value("energi terbarukan").run()
            _assert_clean(self, app)
            self.assertEqual(re.findall(r"<tr><td>(\d+)</td>", _table_html(app)), ["3"])
            self.assertIn(escape(self.claims[2]["text"]), _table_html(app))

            app.text_input(key="claim_search").set_value("").run()
            app.slider(key="threshold_widget").set_value(1.0).run()
            _assert_clean(self, app)
            self.assertEqual(app.session_state["_analysis_threshold"], 1.0)
            expected_flagged = sum(row["greenwashing_probability"] >= 1.0 for row in self.results)
            self.assertEqual(app.session_state["risk_summary"]["flagged_claims"], expected_flagged)

            app.selectbox(key="claim_filter").set_value("Low Indication").run()
            _assert_clean(self, app)
            self.assertEqual(len(re.findall(r"<tr><td>(\d+)</td>", _table_html(app))), len(self.results) - expected_flagged)
            app.run()
            self.assertEqual(app.session_state["original_probabilities"], self.results)
            self.assertEqual(
                [row["greenwashing_probability"] for row in app.session_state["analysis_results"]],
                [row["greenwashing_probability"] for row in self.results],
            )
            for forbidden_call in forbidden:
                forbidden_call.assert_not_called()

    def test_history_restore_navigates_to_dashboard_and_restores_original_threshold(self):
        app = AppTest.from_file(APP_FILE, default_timeout=30)
        self._seed_document(app)
        snapshot = {
            "id": "ui-test-real-indobert-history",
            "date": "2026-09-08T12:00:00+07:00",
            "document_metadata": deepcopy(app.session_state["document_metadata"]),
            "original_probabilities": deepcopy(self.results),
            "risk_summary": deepcopy(self.summary),
            "truncated_claims": 0,
        }
        app.session_state["history"] = [deepcopy(snapshot)]
        with patch("core.inference.predict_batch", side_effect=AssertionError("Unrequested inference")) as inference:
            app.run()
            app.slider(key="threshold_widget").set_value(1.0).run()
            _assert_clean(self, app)
            _navigate(app, "Uji Teks Cepat")
            _assert_clean(self, app)
            _navigate(app, "Analisis Dokumen")
            _assert_clean(self, app)
            self.assertEqual(app.slider(key="threshold_widget").value, 1.0)
            self.assertEqual(app.session_state["original_probabilities"], self.results)

            _navigate(app, "Riwayat")
            _assert_clean(self, app)
            self.assertEqual(app.dataframe[0].value.iloc[0]["Nama Dokumen"], "integration-test-report.pdf")
            self.assertEqual(app.session_state["history"], [snapshot])
            app.button(key="restore_history").click().run()
            _assert_clean(self, app)
            self.assertEqual(app.title[0].value, "Analisis Dokumen")
            self.assertEqual(app.slider(key="threshold_widget").value, self.summary["threshold"])
            self.assertEqual(app.session_state["original_probabilities"], self.results)
            self.assertEqual(app.session_state["risk_summary"], self.summary)
            self.assertEqual(app.session_state["history"], [snapshot])
        inference.assert_not_called()


if __name__ == "__main__":
    unittest.main()
