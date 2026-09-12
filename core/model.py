"""Strict local-only loading, auditable class resolution, and shared model cache."""

from __future__ import annotations

import json
import os
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import streamlit as st
import torch
from safetensors import safe_open
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

from core.settings import MODEL_PATH

POTENTIAL_GREENWASHING = "Potential Greenwashing"
LOW_INDICATION = "Low Indication"
METADATA_FILE = "buto_ijo_v4_metadata.json"


class ModelError(ValueError):
    """An unavailable, incompatible, or ambiguous local checkpoint."""


@dataclass(frozen=True)
class LabelMapping:
    greenwashing_index: int
    low_indication_index: int
    id2label: dict[int, str]
    source: str


@dataclass
class ModelBundle:
    model: Any
    tokenizer: Any
    device: torch.device
    mapping: LabelMapping
    metadata: dict
    config: dict
    path: Path
    max_length: int
    warnings: list[str]
    lock: Any = field(default_factory=threading.RLock, repr=False)


def _canonical(label: str) -> str | None:
    name = re.sub(r"[^a-z0-9]+", " ", str(label).lower()).strip()
    higher = {"higher risk", "high risk", "potential greenwashing", "greenwashing", "indikasi greenwashing", "risiko tinggi"}
    lower = {"lower risk", "low risk", "low indication", "non greenwashing", "not greenwashing", "no greenwashing", "risiko rendah"}
    if name in higher:
        return POTENTIAL_GREENWASHING
    if name in lower:
        return LOW_INDICATION
    return None


def _parse_label_index(value: Any, source: str) -> int:
    """Accept binary integer indices without coercing malformed metadata.

    JSON object keys are strings, while inverse mappings use integer values.
    Booleans and floats must not pass through int(): that would silently turn
    True into class 1 or truncate a fractional index into a different class.
    """
    if type(value) is int and value in (0, 1):
        return value
    if isinstance(value, str) and value in ("0", "1"):
        return int(value)
    raise ModelError(
        f"Index label tidak valid pada {source}. "
        "Model harus memiliki tepat dua kelas dengan index integer 0 dan 1."
    )


def resolve_label_mapping(config: Any, metadata: dict | None = None) -> LabelMapping:
    """Resolve semantic labels; never infer meaning from LABEL_0/LABEL_1.

    Both config directions and any explicit metadata mappings must agree.
    Known risk terminology is translated only for presentation; original names
    and the source of the mapping remain available for audit.
    """
    if not isinstance(config, dict):
        config = config.to_dict() if hasattr(config, "to_dict") else vars(config)
    metadata = metadata or {}
    resolved: dict[int, str] = {}
    originals: dict[int, str] = {}
    sources: list[str] = []

    def consume(mapping: dict, direction: str, source: str) -> None:
        if not isinstance(mapping, dict):
            raise ModelError(f"Mapping label tidak valid pada {source}.")
        for key, value in mapping.items():
            index, label = (
                (_parse_label_index(key, source), str(value))
                if direction == "id2label"
                else (_parse_label_index(value, source), str(key))
            )
            meaning = _canonical(label)
            originals.setdefault(index, label)
            if meaning is None:
                continue
            if index in resolved and resolved[index] != meaning:
                raise ModelError(f"Konflik mapping label index {index} antara config dan metadata.")
            resolved[index] = meaning
            originals[index] = label
            if source not in sources:
                sources.append(source)

    def check_directions(obj: dict, source: str) -> None:
        if "id2label" not in obj or "label2id" not in obj:
            return
        try:
            forward = {_parse_label_index(k, source): str(v) for k, v in obj["id2label"].items()}
            inverse = {str(k): _parse_label_index(v, source) for k, v in obj["label2id"].items()}
        except (AttributeError, TypeError, ValueError) as exc:
            raise ModelError(f"Mapping label tidak valid pada {source}.") from exc
        if {label: index for index, label in forward.items()} != inverse or len(set(forward.values())) != len(forward):
            raise ModelError(f"Konflik id2label dan label2id pada {source}.")

    for source, obj in (("config", config), ("metadata", metadata)):
        check_directions(obj, source)
        for direction in ("id2label", "label2id"):
            if direction in obj:
                consume(obj[direction], direction, f"{source}.{direction}")
    extra = metadata.get("label_mapping")
    if isinstance(extra, dict):
        check_directions(extra, "metadata.label_mapping")
        nested = False
        for direction in ("id2label", "label2id"):
            if direction in extra:
                consume(extra[direction], direction, f"metadata.label_mapping.{direction}")
                nested = True
        if not nested:
            direction = "id2label" if all(str(k).isdigit() for k in extra) else "label2id"
            consume(extra, direction, "metadata.label_mapping")
    for key in ("greenwashing_index", "greenwashing_label_id", "higher_risk_label_id"):
        if key in metadata:
            consume({POTENTIAL_GREENWASHING: metadata[key]}, "label2id", f"metadata.{key}")
    # An explicit semantic positive index determines the other class of a binary model.
    if len(resolved) == 1 and set(resolved.values()) == {POTENTIAL_GREENWASHING}:
        other = 1 - next(iter(resolved))
        resolved[other] = LOW_INDICATION
    if set(resolved) != {0, 1} or set(resolved.values()) != {POTENTIAL_GREENWASHING, LOW_INDICATION}:
        raise ModelError(
            "Arti label model belum dapat dipastikan. Lengkapi id2label/label2id "
            "di config atau mapping eksplisit pada metadata. LABEL_1 tidak otomatis berarti greenwashing."
        )
    positive = next(i for i, name in resolved.items() if name == POTENTIAL_GREENWASHING)
    return LabelMapping(positive, 1 - positive, originals, ", ".join(sources))


def _read_json(path: Path, optional: bool = False) -> dict:
    if optional and not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError("JSON bukan object")
        return value
    except (OSError, ValueError) as exc:
        raise ModelError(f"Tidak dapat membaca {path.name}: {exc}") from exc


def resolve_model_path(model_path: str | Path = MODEL_PATH) -> Path:
    path = Path(model_path).expanduser().resolve()
    if not path.is_dir():
        raise ModelError(f"Folder model tidak ditemukan: {path}. Atur BUTO_IJO_MODEL_PATH ke folder model lokal.")
    if (path / "config.json").is_file():
        return path
    candidates = [p.parent for p in path.glob("*/config.json") if (p.parent / "model.safetensors").is_file()]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ModelError("Beberapa model ditemukan. Atur BUTO_IJO_MODEL_PATH ke satu folder checkpoint yang spesifik.")
    raise ModelError(f"config.json dan model.safetensors tidak ditemukan di {path} atau satu subfoldernya.")


def inspect_model(model_path: str = MODEL_PATH) -> dict:
    """Read configuration and tensor shapes without loading 498 MB of weights."""
    path = resolve_model_path(model_path)
    config = _read_json(path / "config.json")
    metadata = _read_json(path / METADATA_FILE, optional=True)
    mapping = resolve_label_mapping(config, metadata)
    warnings: list[str] = []
    if not metadata:
        warnings.append("Tidak tersedia pada metadata model.")
    if config.get("_num_labels", 2) != 2:
        warnings.append(
            f"Config menyimpan field lama _num_labels={config['_num_labels']}; "
            "id2label dan dimensi classifier pada bobot asli berjumlah 2."
        )
    weights = path / "model.safetensors"
    if not weights.is_file():
        raise ModelError(f"Bobot model.safetensors tidak ditemukan di {path}.")
    try:
        with safe_open(str(weights), framework="pt", device="cpu") as tensors:
            if "classifier.weight" not in tensors.keys():
                raise ModelError("Checkpoint tidak memiliki classifier.weight IndoBERT yang diharapkan.")
            shape = tensors.get_slice("classifier.weight").get_shape()
            bias = tensors.get_slice("classifier.bias").get_shape()
            if shape != [2, config.get("hidden_size")] or bias != [2]:
                raise ModelError(f"Dimensi classifier bukan binary classifier yang sesuai config: {shape}, bias {bias}.")
    except ModelError:
        raise
    except Exception as exc:
        raise ModelError(f"Bobot safetensors tidak valid: {exc}") from exc
    return {
        "path": path, "config": config, "metadata": metadata, "mapping": mapping,
        "warnings": warnings, "max_length": min(512, int(config.get("max_position_embeddings", 512))),
        "device": "CUDA" if torch.cuda.is_available() else "CPU",
    }


@st.cache_resource(show_spinner=False)
def load_model(model_path: str = MODEL_PATH) -> ModelBundle:
    """Load the supplied, complete checkpoint once, with no download or retraining."""
    info = inspect_model(model_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    try:
        # Bounded CPU parallelism avoids oversubscription across Streamlit sessions.
        threads = int(os.getenv("BUTO_IJO_TORCH_THREADS", str(min(4, os.cpu_count() or 1))))
        if not 1 <= threads <= 64:
            raise ValueError("BUTO_IJO_TORCH_THREADS harus antara 1 dan 64")
        torch.set_num_threads(threads)
        config = AutoConfig.from_pretrained(str(info["path"]), local_files_only=True, trust_remote_code=False)
        if config.num_labels != 2:
            raise ModelError(f"Config efektif memiliki {config.num_labels} kelas, bukan 2.")
        tokenizer = AutoTokenizer.from_pretrained(str(info["path"]), local_files_only=True, trust_remote_code=False)
        model, loading_info = AutoModelForSequenceClassification.from_pretrained(
            str(info["path"]), config=config, local_files_only=True, trust_remote_code=False,
            use_safetensors=True, output_loading_info=True,
        )
        # Transformers may initialize absent weights; those must NEVER reach inference.
        failures = {k: loading_info[k] for k in ("missing_keys", "mismatched_keys", "error_msgs") if loading_info.get(k)}
        if failures:
            raise ModelError(f"Checkpoint tidak lengkap/cocok; inference dibatalkan agar tidak memakai bobot baru: {failures}")
        if loading_info.get("unexpected_keys"):
            info["warnings"].append(f"Tensor tambahan pada checkpoint: {', '.join(loading_info['unexpected_keys'])}")
        mapping = resolve_label_mapping(model.config, info["metadata"])
        model.to(device)
        model.eval()
        max_length = min(info["max_length"], tokenizer.model_max_length)
        return ModelBundle(model, tokenizer, device, mapping, info["metadata"], info["config"], info["path"], int(max_length), info["warnings"])
    except ModelError:
        raise
    except Exception as exc:
        raise ModelError(f"Model lokal gagal dimuat: {exc}. Periksa kelengkapan checkpoint dan dependensi.") from exc
