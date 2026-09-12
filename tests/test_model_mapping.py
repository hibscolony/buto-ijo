"""Semantic label resolution must never assume that class index 1 is positive."""

from types import SimpleNamespace
import unittest

from core.model import ModelError, resolve_label_mapping, resolve_model_path


class LabelMappingTests(unittest.TestCase):
    def test_actual_checkpoint_label_vocabulary(self):
        config = {
            "_num_labels": 5,  # The supplied checkpoint contains this stale field.
            "id2label": {"0": "Lower Risk", "1": "Higher Risk"},
            "label2id": {"Higher Risk": 1, "Lower Risk": 0},
        }
        metadata = {
            "risk_definition": {
                "Higher Risk": "evidence score 0-4",
                "Lower Risk": "evidence score 5-10",
            }
        }
        mapping = resolve_label_mapping(config, metadata)
        self.assertEqual(mapping.greenwashing_index, 1)
        self.assertEqual(mapping.low_indication_index, 0)
        self.assertEqual(mapping.id2label, {0: "Lower Risk", 1: "Higher Risk"})
        self.assertIn("config.id2label", mapping.source)

    def test_reversed_semantic_labels_resolve_class_zero_as_positive(self):
        config = SimpleNamespace(
            id2label={0: "Potential Greenwashing", 1: "Low Indication"},
            label2id={"Potential Greenwashing": 0, "Low Indication": 1},
        )
        mapping = resolve_label_mapping(config, {})
        self.assertEqual(mapping.greenwashing_index, 0)
        self.assertEqual(mapping.low_indication_index, 1)

    def test_generic_labels_without_explicit_metadata_are_ambiguous(self):
        config = {
            "id2label": {"0": "LABEL_0", "1": "LABEL_1"},
            "label2id": {"LABEL_0": 0, "LABEL_1": 1},
        }
        with self.assertRaisesRegex(ModelError, "belum dapat dipastikan"):
            resolve_label_mapping(config, {})
        with self.assertRaises(ModelError):
            resolve_label_mapping(config, {"risk_definition": {"Higher Risk": "evidence score 0-4"}})

    def test_metadata_can_explicitly_resolve_generic_labels_in_either_direction(self):
        generic = {"id2label": {"0": "LABEL_0", "1": "LABEL_1"}}
        variants = [
            {"id2label": {"0": "Higher Risk", "1": "Lower Risk"}},
            {"label2id": {"Higher Risk": 0, "Lower Risk": 1}},
            {"label_mapping": {"0": "Higher Risk", "1": "Lower Risk"}},
            {"label_mapping": {"id2label": {"0": "Higher Risk", "1": "Lower Risk"}}},
            {"greenwashing_index": 0},
        ]
        for metadata in variants:
            with self.subTest(metadata=metadata):
                mapping = resolve_label_mapping(generic, metadata)
                self.assertEqual(mapping.greenwashing_index, 0)
                self.assertEqual(mapping.low_indication_index, 1)
                self.assertIn("metadata", mapping.source)

    def test_conflicting_config_directions_are_rejected(self):
        config = {
            "id2label": {"0": "Lower Risk", "1": "Higher Risk"},
            "label2id": {"Higher Risk": 0, "Lower Risk": 1},
        }
        with self.assertRaisesRegex(ModelError, "Konflik"):
            resolve_label_mapping(config, {})

    def test_conflicting_metadata_is_rejected(self):
        config = {"id2label": {"0": "Lower Risk", "1": "Higher Risk"}}
        with self.assertRaisesRegex(ModelError, "Konflik"):
            resolve_label_mapping(config, {"greenwashing_index": 0})

    def test_generic_direction_conflict_is_not_masked_by_semantic_metadata(self):
        config = {
            "id2label": {"0": "LABEL_0", "1": "LABEL_1"},
            "label2id": {"LABEL_0": 1, "LABEL_1": 0},
        }
        with self.assertRaisesRegex(ModelError, "Konflik"):
            resolve_label_mapping(config, {"greenwashing_index": 1})

    def test_nonbinary_and_duplicate_semantic_classes_are_rejected(self):
        invalid_mappings = [
            {"0": "Lower Risk", "1": "Higher Risk", "2": "Neutral"},
            {"0": "Higher Risk", "1": "Potential Greenwashing"},
            {"0": "Lower Risk", "1": "Low Indication"},
        ]
        for mapping in invalid_mappings:
            with self.subTest(mapping=mapping):
                with self.assertRaises(ModelError):
                    resolve_label_mapping({"id2label": mapping}, {})

    def test_missing_model_path_has_actionable_error(self):
        with self.assertRaisesRegex(ModelError, "BUTO_IJO_MODEL_PATH"):
            resolve_model_path("tests/nonexistent-model-checkpoint-for-test")


if __name__ == "__main__":
    unittest.main()
