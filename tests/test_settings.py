"""Cross-platform model-path selection for desktop and cloud deployment."""

from pathlib import Path
import unittest

from core.settings import configured_model_path, default_model_path


class ModelPathSettingsTests(unittest.TestCase):
    def test_linux_defaults_to_bundled_checkpoint(self):
        bundled = Path("/srv/buto-ijo/_models/BUTO_IJO_v4_IndoBERT")
        self.assertEqual(default_model_path("posix", bundled), str(bundled))

    def test_linux_ignores_stale_windows_environment_path(self):
        bundled = Path("/mount/src/buto-ijo/_models/BUTO_IJO_v4_IndoBERT")
        actual = configured_model_path(
            {"BUTO_IJO_MODEL_PATH": r"E:\Downloads\Buto Ijo\_models"},
            platform_name="posix",
            bundled_model_path=bundled,
        )
        self.assertEqual(actual, str(bundled))

    def test_native_and_relative_environment_overrides_remain_supported(self):
        bundled = Path("/srv/default")
        self.assertEqual(
            configured_model_path({"BUTO_IJO_MODEL_PATH": "/models/checkpoint"}, "posix", bundled),
            "/models/checkpoint",
        )
        self.assertEqual(
            configured_model_path({"BUTO_IJO_MODEL_PATH": "./custom-model"}, "posix", bundled),
            "./custom-model",
        )


if __name__ == "__main__":
    unittest.main()
