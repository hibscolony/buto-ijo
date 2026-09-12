"""Validated environment configuration; never downloads a remote model."""

import os
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_MODEL_PATH = PROJECT_ROOT / "_models" / "BUTO_IJO_v4_IndoBERT"
WINDOWS_MODEL_PATH = Path(r"E:\Downloads\Buto Ijo\_models")


def default_model_path(
    platform_name: str | None = None,
    bundled_model_path: Path | None = None,
    windows_model_path: Path | None = None,
) -> str:
    """Choose a real local checkpoint path for desktop and Linux deployment."""
    platform_name = platform_name or os.name
    bundled_model_path = bundled_model_path or BUNDLED_MODEL_PATH
    windows_model_path = windows_model_path or WINDOWS_MODEL_PATH
    if bundled_model_path.is_dir():
        return str(bundled_model_path)
    if platform_name == "nt":
        return str(windows_model_path)
    return str(bundled_model_path)


def configured_model_path(
    environment: dict[str, str] | os._Environ[str] | None = None,
    platform_name: str | None = None,
    bundled_model_path: Path | None = None,
) -> str:
    """Apply an environment override without treating a Windows path as relative on Linux."""
    environment = os.environ if environment is None else environment
    platform_name = platform_name or os.name
    bundled_model_path = bundled_model_path or BUNDLED_MODEL_PATH
    configured = environment.get("BUTO_IJO_MODEL_PATH", "").strip()
    if configured:
        if platform_name != "nt" and PureWindowsPath(configured).is_absolute():
            return str(bundled_model_path)
        return configured
    return default_model_path(platform_name, bundled_model_path)


MODEL_PATH = default_model_path()
BATCH_SIZE = 16
MAX_LENGTH = 512
MIN_CHAR_LENGTH = 25


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} harus berupa bilangan bulat.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} harus antara {minimum} dan {maximum}.")
    return value


@dataclass(frozen=True)
class Settings:
    model_path: str = MODEL_PATH
    batch_size: int = BATCH_SIZE
    max_length: int = MAX_LENGTH
    min_char_length: int = MIN_CHAR_LENGTH
    max_upload_mb: int = 50
    default_threshold: float = 0.50


def get_settings() -> Settings:
    return Settings(
        model_path=configured_model_path(),
        batch_size=_integer("BUTO_IJO_BATCH_SIZE", BATCH_SIZE, 1, 128),
        max_length=_integer("BUTO_IJO_MAX_LENGTH", MAX_LENGTH, 8, 512),
        min_char_length=_integer("BUTO_IJO_MIN_CHAR_LENGTH", MIN_CHAR_LENGTH, 1, 1000),
        max_upload_mb=_integer("BUTO_IJO_MAX_UPLOAD_MB", 50, 1, 200),
    )
