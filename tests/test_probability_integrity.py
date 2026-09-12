"""Thresholding preserves stored softmax values; fixtures test arithmetic only."""

from copy import deepcopy
import unittest

from core.risk import NEGATIVE_LABEL, POSITIVE_LABEL, apply_threshold


class ProbabilityIntegrityTests(unittest.TestCase):
    def test_threshold_preserves_exact_negative_class_softmax(self):
        # Representative float32 values need not sum exactly to one in float64.
        positive = 0.7999999523162842
        negative = 0.20000000298023224
        original = [{
            "claim_id": 1,
            "greenwashing_probability": positive,
            "probabilities": {POSITIVE_LABEL: positive, NEGATIVE_LABEL: negative},
        }]
        snapshot = deepcopy(original)
        low_result = apply_threshold(original, threshold=0.9)[0]
        self.assertEqual(low_result["prediction"], NEGATIVE_LABEL)
        self.assertEqual(low_result["confidence"], negative)
        self.assertNotEqual(low_result["confidence"], 1.0 - positive)
        self.assertEqual(original, snapshot)

        high_result = apply_threshold(original, threshold=0.5)[0]
        self.assertEqual(high_result["prediction"], POSITIVE_LABEL)
        self.assertEqual(high_result["confidence"], positive)

    def test_probability_only_inputs_keep_complement_fallback(self):
        result = apply_threshold([{"greenwashing_probability": 0.2}])[0]
        self.assertEqual(result["confidence"], 0.8)

    def test_rejects_invalid_or_inconsistent_stored_negative_probability(self):
        for negative in (float("nan"), float("inf"), -0.1, 1.1, 0.9):
            with self.subTest(negative=negative), self.assertRaises(ValueError):
                apply_threshold([{
                    "greenwashing_probability": 0.8,
                    "probabilities": {NEGATIVE_LABEL: negative},
                }])

    def test_rejects_malformed_class_probability_mapping(self):
        with self.assertRaises(ValueError):
            apply_threshold([{"greenwashing_probability": 0.2, "probabilities": [0.2, 0.8]}])


if __name__ == "__main__":
    unittest.main()
