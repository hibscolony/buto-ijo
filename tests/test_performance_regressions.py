"""Cache invalidation coverage without substituting for model predictions.

Upload tests use real local parsing. Result-view tests are opt-in and use the
actual local checkpoint, consistent with the existing UI integration tests.
"""

from copy import deepcopy
import csv
from hashlib import sha256
from io import BytesIO, StringIO
import os
import unittest
from unittest.mock import patch

from streamlit.proto.Common_pb2 import FileURLs
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec

from core.document_parser import DocumentError
from core.settings import Settings
from pages import document_analysis


def _uploaded(data: bytes, file_id: str = "report-1", name: str = "report.txt") -> UploadedFile:
    return UploadedFile(UploadedFileRec(file_id, name, "text/plain", data), FileURLs())


class UploadCacheRegressionTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        state_patch = patch.object(document_analysis.st, "session_state", self.state)
        state_patch.start()
        self.addCleanup(state_patch.stop)

    def test_native_upload_is_hashed_and_parsed_once_across_reruns(self):
        data = b"Emisi karbon perusahaan turun sebesar 20% pada tahun 2024."
        with patch.object(document_analysis, "sha256", wraps=sha256) as hasher, patch.object(
            document_analysis, "parse_document", wraps=document_analysis.parse_document
        ) as parser:
            first = document_analysis._prepare_upload(_uploaded(data), Settings())
            for _ in range(3):
                # Streamlit may reconstruct its UploadedFile object on a rerun.
                uploaded = _uploaded(data)
                again = document_analysis._prepare_upload(uploaded, Settings())
                signature = document_analysis._upload_signature(uploaded)
                self.assertIs(again, first)
                self.assertEqual(signature, first["signature"])
        self.assertEqual(hasher.call_count, 1)
        self.assertEqual(parser.call_count, 1)
        self.assertEqual(first["signature"], sha256(b"report.txt" + data).hexdigest())

    def test_new_file_id_with_same_name_and_size_invalidates_upload(self):
        old_data = b"Emisi karbon perusahaan turun sebesar 20% pada tahun 2024."
        new_data = b"Emisi karbon perusahaan turun sebesar 30% pada tahun 2024."
        self.assertEqual(len(old_data), len(new_data))
        with patch.object(document_analysis, "sha256", wraps=sha256) as hasher, patch.object(
            document_analysis, "parse_document", wraps=document_analysis.parse_document
        ) as parser:
            first = document_analysis._prepare_upload(_uploaded(old_data, "old"), Settings())
            second = document_analysis._prepare_upload(_uploaded(new_data, "new"), Settings())
        self.assertEqual(hasher.call_count, 2)
        self.assertEqual(parser.call_count, 2)
        self.assertIsNot(first, second)
        self.assertNotEqual(first["signature"], second["signature"])
        self.assertIn("30%", second["pages"][0]["text"])

    def test_generic_stream_rechecks_changed_bytes_even_at_same_size(self):
        uploaded = BytesIO(b"Emisi karbon turun sebesar 20% pada tahun 2024.")
        uploaded.name = "report.txt"
        first = document_analysis._prepare_upload(uploaded, Settings())
        uploaded.seek(0)
        uploaded.write(b"Emisi karbon turun sebesar 30% pada tahun 2024.")
        second = document_analysis._prepare_upload(uploaded, Settings())
        self.assertNotEqual(first["signature"], second["signature"])
        self.assertIn("30%", second["pages"][0]["text"])

    def test_cached_upload_still_obeys_a_lower_upload_limit(self):
        data = b"Laporan emisi karbon perusahaan. " + b" " * (1024 * 1024)
        prepared = document_analysis._prepare_upload(_uploaded(data), Settings(max_upload_mb=2))
        with patch.object(document_analysis, "parse_document") as parser:
            with self.assertRaisesRegex(DocumentError, "melebihi batas 1 MB"):
                document_analysis._prepare_upload(_uploaded(data), Settings(max_upload_mb=1))
        parser.assert_not_called()
        self.assertIs(self.state["_prepared_upload"], prepared)

    def test_parse_failure_keeps_previous_document_and_new_signature_distinct(self):
        prepared = document_analysis._prepare_upload(
            _uploaded(b"Laporan emisi karbon perusahaan untuk tahun 2024."), Settings()
        )
        broken = _uploaded(b"This is not a valid PDF", "broken", "broken-report.pdf")
        with self.assertRaises(DocumentError):
            document_analysis._prepare_upload(broken, Settings())
        self.assertIs(self.state["_prepared_upload"], prepared)
        # This comparison drives the previous-document attribution notice.
        self.assertNotEqual(
            document_analysis._upload_signature(broken), prepared["metadata"]["signature"]
        )


@unittest.skipUnless(
    os.getenv("BUTO_IJO_RUN_MODEL_TESTS") == "1",
    "Set BUTO_IJO_RUN_MODEL_TESTS=1 for caches containing actual model probabilities.",
)
class RealProbabilityViewCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core.inference import predict_batch
        from core.model import load_model
        from core.settings import get_settings

        configured = get_settings()
        settings = Settings(model_path=configured.model_path, batch_size=2, max_length=64)
        cls.predictions = predict_batch([
            {"claim_id": 1, "page": 1,
             "text": "Penggunaan energi terbarukan mencapai 30% dari konsumsi energi perusahaan."},
            {"claim_id": 2, "page": 2,
             "text": "Kami berkomitmen menjaga lingkungan untuk masa depan yang lebih hijau."},
        ], bundle=load_model(settings.model_path), settings=settings)

    def setUp(self):
        self.state = {}
        self.originals = deepcopy(self.predictions)
        state_patch = patch.object(document_analysis.st, "session_state", self.state)
        state_patch.start()
        self.addCleanup(state_patch.stop)

    def test_unchanged_probabilities_and_threshold_reuse_derived_view(self):
        snapshot = deepcopy(self.originals)
        with patch.object(
            document_analysis, "apply_threshold", wraps=document_analysis.apply_threshold
        ) as classify, patch.object(
            document_analysis, "calculate_document_risk", wraps=document_analysis.calculate_document_risk
        ) as aggregate, patch.object(
            document_analysis, "results_to_csv", wraps=document_analysis.results_to_csv
        ) as export:
            first = document_analysis._result_view(self.originals, 0.36)
            for _ in range(3):
                self.assertIs(document_analysis._result_view(self.originals, 0.36), first)
        self.assertEqual(classify.call_count, 1)
        self.assertEqual(aggregate.call_count, 1)
        self.assertEqual(export.call_count, 1)
        self.assertIs(first["originals"], self.originals)
        self.assertEqual(self.originals, snapshot)

    def test_replacement_probability_list_invalidates_at_unchanged_threshold(self):
        first = document_analysis._result_view(self.originals, 0.36)
        replacement = deepcopy(self.originals)
        with patch.object(
            document_analysis, "results_to_csv", wraps=document_analysis.results_to_csv
        ) as export:
            second = document_analysis._result_view(replacement, 0.36)
        self.assertIsNot(first, second)
        self.assertIs(second["originals"], replacement)
        self.assertEqual(second["results"], first["results"])
        self.assertEqual(export.call_count, 1)

    def test_threshold_change_refreshes_summary_and_export_without_mutating_probabilities(self):
        from core.risk import NEGATIVE_LABEL, POSITIVE_LABEL

        snapshot = deepcopy(self.originals)
        first = document_analysis._result_view(self.originals, 0.0)
        second = document_analysis._result_view(self.originals, 1.0)
        self.assertIsNot(first, second)
        self.assertEqual(self.originals, snapshot)
        for threshold, view in ((0.0, first), (1.0, second)):
            self.assertEqual(view["summary"]["threshold"], threshold)
            self.assertEqual(view["summary"]["flagged_claims"], sum(
                row["greenwashing_probability"] >= threshold for row in self.originals
            ))
            exported = list(csv.DictReader(StringIO(view["csv"].decode("utf-8-sig"))))
            self.assertEqual(len(exported), len(self.originals))
            for original, row in zip(self.originals, exported):
                probability = original["greenwashing_probability"]
                label = POSITIVE_LABEL if probability >= threshold else NEGATIVE_LABEL
                self.assertEqual(row["prediction"], label)
                self.assertEqual(float(row["greenwashing_probability"]), probability)
                self.assertEqual(float(row["confidence"]), original["probabilities"][label])


if __name__ == "__main__":
    unittest.main()
