"""Opt-in integration tests using the user's actual, local IndoBERT weights.

Run with BUTO_IJO_RUN_MODEL_TESTS=1. No network downloads, mock model,
fabricated logits, training, or random prediction fallback is used.
"""

import os
import unittest


@unittest.skipUnless(
    os.getenv("BUTO_IJO_RUN_MODEL_TESTS") == "1",
    "Set BUTO_IJO_RUN_MODEL_TESTS=1 to run actual local-model integration tests.",
)
class RealModelIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch

        from core.model import load_model
        from core.settings import Settings, get_settings

        cls.torch = torch
        configured = get_settings()
        cls.settings = Settings(
            model_path=configured.model_path,
            batch_size=2,
            max_length=64,
            min_char_length=25,
        )
        cls.bundle = load_model(cls.settings.model_path)
        cls.claims = [
            {
                "claim_id": 1,
                "page": 2,
                "text": "Kami berkomitmen menjaga lingkungan untuk masa depan yang lebih hijau.",
            },
            {
                "claim_id": 2,
                "page": 9,
                "text": "Emisi gas rumah kaca turun 12,5% pada 2024 dibandingkan tahun dasar 2020.",
            },
            {
                "claim_id": 3,
                "page": 10,
                "text": "Penggunaan energi terbarukan meningkat menjadi 30% dari total konsumsi energi.",
            },
        ]

    def test_model_is_cached_and_in_eval_mode(self):
        from core.model import load_model

        self.assertIs(self.bundle, load_model(self.settings.model_path))
        self.assertFalse(self.bundle.model.training)
        expected_device = "cuda" if self.torch.cuda.is_available() else "cpu"
        self.assertEqual(self.bundle.device.type, expected_device)
        self.assertEqual(self.bundle.model.config.num_labels, 2)

    def test_batches_match_direct_softmax_and_disable_gradients(self):
        from core.inference import predict_batch

        forward_calls = []

        def observe_forward(_module, _arguments, output):
            forward_calls.append(
                (self.torch.is_grad_enabled(), output.logits.requires_grad)
            )

        hook = self.bundle.model.register_forward_hook(observe_forward)
        try:
            predictions = predict_batch(
                self.claims, bundle=self.bundle, settings=self.settings
            )
        finally:
            hook.remove()

        self.assertEqual(len(predictions), len(self.claims))
        self.assertEqual(len(forward_calls), 2, "Three claims must use two size-2 batches.")
        self.assertTrue(all(call == (False, False) for call in forward_calls))

        from core.preprocessing import format_model_input
        from core.risk import NEGATIVE_LABEL, POSITIVE_LABEL

        texts = [format_model_input(claim["text"]) for claim in self.claims]
        encoded = self.bundle.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.settings.max_length,
            return_tensors="pt",
        )
        encoded = {key: value.to(self.bundle.device) for key, value in encoded.items()}
        with self.torch.no_grad():
            direct_probabilities = self.torch.softmax(
                self.bundle.model(**encoded).logits, dim=-1
            ).cpu().tolist()

        for claim, prediction, direct in zip(self.claims, predictions, direct_probabilities):
            positive = direct[self.bundle.mapping.greenwashing_index]
            negative = direct[self.bundle.mapping.low_indication_index]
            self.assertEqual(prediction["claim_id"], claim["claim_id"])
            self.assertEqual(prediction["page"], claim["page"])
            self.assertEqual(prediction["claim"], claim["text"])
            self.assertAlmostEqual(prediction["greenwashing_probability"], positive, delta=1e-4)
            self.assertAlmostEqual(
                prediction["probabilities"][POSITIVE_LABEL], positive, delta=1e-4
            )
            self.assertAlmostEqual(
                prediction["probabilities"][NEGATIVE_LABEL], negative, delta=1e-4
            )
            self.assertAlmostEqual(sum(prediction["probabilities"].values()), 1.0, places=5)
            expected_label = POSITIVE_LABEL if positive >= self.settings.default_threshold else NEGATIVE_LABEL
            self.assertEqual(prediction["prediction"], expected_label)

    def test_single_claim_matches_batch(self):
        from core.inference import predict_batch, predict_text

        single = predict_text(
            self.claims[0]["text"], bundle=self.bundle, settings=self.settings
        )
        batched = predict_batch(
            self.claims[:2], bundle=self.bundle, settings=self.settings
        )[0]
        self.assertAlmostEqual(
            single["greenwashing_probability"],
            batched["greenwashing_probability"],
            delta=1e-4,
        )

    def test_threshold_updates_use_stored_real_probabilities(self):
        from core.inference import predict_batch
        from core.risk import apply_threshold, calculate_document_risk

        predictions = predict_batch(
            self.claims, bundle=self.bundle, settings=self.settings
        )
        original_probabilities = [row["greenwashing_probability"] for row in predictions]
        forward_calls = []
        hook = self.bundle.model.register_forward_hook(
            lambda *_args: forward_calls.append(True)
        )
        try:
            updated = apply_threshold(predictions, threshold=0.95)
            summary = calculate_document_risk(updated, threshold=0.95)
        finally:
            hook.remove()
        self.assertEqual(forward_calls, [], "Threshold changes must not call the model.")
        self.assertEqual(
            [row["greenwashing_probability"] for row in updated], original_probabilities
        )
        self.assertEqual(summary["total_claims"], len(self.claims))

    def test_document_pipeline_preserves_pages_and_reports_truncation(self):
        from core.inference import analyze_document, predict_text

        report = analyze_document(
            [{"page": row["page"], "text": row["text"]} for row in self.claims],
            bundle=self.bundle,
            settings=self.settings,
        )
        self.assertEqual(report["claim_count"], 3)
        self.assertEqual([row["page"] for row in report["results"]], [2, 9, 10])
        self.assertEqual(report["risk_summary"]["total_claims"], 3)
        self.assertEqual(len(report["original_probabilities"]), 3)
        long_claim = "Pengurangan emisi karbon perusahaan meningkat secara berkelanjutan " * 100
        truncated = predict_text(long_claim, bundle=self.bundle, settings=self.settings)
        self.assertTrue(truncated["truncated"])
        self.assertGreaterEqual(truncated["greenwashing_probability"], 0.0)
        self.assertLessEqual(truncated["greenwashing_probability"], 1.0)


if __name__ == "__main__":
    unittest.main()
