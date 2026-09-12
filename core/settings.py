"""Validated environment configuration; never downloads a remote model."""

import os
from dataclasses import dataclass

MODEL_PATH = r"E:\Downloads\Buto Ijo\_models"
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
        model_path=os.getenv("BUTO_IJO_MODEL_PATH", MODEL_PATH),
        batch_size=_integer("BUTO_IJO_BATCH_SIZE", BATCH_SIZE, 1, 128),
        max_length=_integer("BUTO_IJO_MAX_LENGTH", MAX_LENGTH, 8, 512),
        min_char_length=_integer("BUTO_IJO_MIN_CHAR_LENGTH", MIN_CHAR_LENGTH, 1, 1000),
        max_upload_mb=_integer("BUTO_IJO_MAX_UPLOAD_MB", 50, 1, 200),
    )
