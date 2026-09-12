"""Real PyTorch softmax inference; UI threshold changes use stored probabilities."""

from __future__ import annotations

from copy import deepcopy
from typing import Callable

import torch

from core.model import LOW_INDICATION, POTENTIAL_GREENWASHING, ModelBundle, load_model
from core.preprocessing import build_claims, clean_text
from core.risk import calculate_document_risk
from core.settings import Settings, get_settings

ProgressCallback = Callable[[float, str], None]


class InferenceError(RuntimeError):
    """Inference failed without returning any partial/fabricated result."""


def predict_batch(
    claims: list[dict], bundle: ModelBundle | None = None, settings: Settings | None = None,
    threshold: float = 0.5, progress_callback: ProgressCallback | None = None,
) -> list[dict]:
    if not claims:
        raise ValueError("Tidak ada klaim yang dapat dianalisis.")
    if not 0 <= threshold <= 1:
        raise ValueError("Threshold harus antara 0 dan 1.")
    settings = settings or get_settings()
    if settings.batch_size < 1 or settings.max_length < 8:
        raise ValueError("Batch size minimal 1 dan maximum sequence length minimal 8.")
    bundle = bundle or load_model(settings.model_path)
    max_length = min(settings.max_length, bundle.max_length)
    results: list[dict] = []
    try:
        for start in range(0, len(claims), settings.batch_size):
            batch = claims[start:start + settings.batch_size]
            texts = [clean_text(item.get("text", item.get("claim", ""))) for item in batch]
            if any(not text for text in texts):
                raise ValueError("Terdapat teks klaim kosong.")
            with bundle.lock:
                # Count bounded tokens separately to report truncation honestly.
                lengths = bundle.tokenizer(texts, padding=False, truncation=True, max_length=max_length + 1, return_length=True)["length"]
                inputs = bundle.tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
                inputs = {key: tensor.to(bundle.device) for key, tensor in inputs.items()}
                bundle.model.eval()
                with torch.no_grad():
                    logits = bundle.model(**inputs).logits
                    if logits.shape != (len(batch), 2):
                        raise InferenceError(f"Bentuk logits tidak sesuai binary classifier: {tuple(logits.shape)}.")
                    probabilities = torch.softmax(logits, dim=-1).cpu()
                if not torch.isfinite(probabilities).all():
                    raise InferenceError("Model menghasilkan probability tidak valid.")
            for item, text, probs, token_length in zip(batch, texts, probabilities.tolist(), lengths):
                green = float(probs[bundle.mapping.greenwashing_index])
                low = float(probs[bundle.mapping.low_indication_index])
                results.append({
                    "claim_id": item.get("claim_id", len(results) + 1), "claim": text, "page": item.get("page"),
                    "prediction": POTENTIAL_GREENWASHING if green >= threshold else LOW_INDICATION,
                    "greenwashing_probability": green, "confidence": green if green >= threshold else low,
                    "probabilities": {POTENTIAL_GREENWASHING: green, LOW_INDICATION: low},
                    "truncated": token_length > max_length,
                })
            if progress_callback:
                progress_callback(min((start + len(batch)) / len(claims), 1.0), f"Running IndoBERT · {start + len(batch):,}/{len(claims):,} klaim")
    except InferenceError:
        raise
    except Exception as exc:
        message = "Memori perangkat tidak mencukupi. Turunkan BUTO_IJO_BATCH_SIZE." if "out of memory" in str(exc).lower() else str(exc)
        raise InferenceError(f"Inference IndoBERT gagal: {message}") from exc
    return results


def predict_text(
    text: str, bundle: ModelBundle | None = None, settings: Settings | None = None, threshold: float = 0.5,
) -> dict:
    text = clean_text(text)
    if not text:
        raise ValueError("Teks kosong. Masukkan klaim keberlanjutan terlebih dahulu.")
    return predict_batch([{"claim_id": 1, "page": None, "text": text}], bundle, settings, threshold)[0]


def analyze_document(
    pages: list[dict], settings: Settings | None = None, bundle: ModelBundle | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    settings = settings or get_settings()

    def progress(value: float, message: str) -> None:
        if progress_callback:
            progress_callback(value, message)

    progress(0.1, "Segmenting claims · membersihkan dan memisahkan kalimat")
    claims = build_claims(pages, min_char_length=settings.min_char_length)
    if not claims:
        raise ValueError(f"Tidak ada kalimat yang memenuhi panjang minimum {settings.min_char_length} karakter.")
    progress(0.2, f"Running IndoBERT · {len(claims):,} klaim")
    results = predict_batch(
        claims, bundle=bundle, settings=settings, threshold=settings.default_threshold,
        progress_callback=lambda value, message: progress(0.2 + 0.7 * value, message),
    )
    progress(0.94, "Aggregating results · menghitung Risk Index")
    summary = calculate_document_risk(results, threshold=settings.default_threshold)
    progress(1.0, "Analisis selesai")
    return {
        "results": results, "original_probabilities": deepcopy(results), "risk_summary": summary,
        "claim_count": len(results), "truncated_claims": sum(r["truncated"] for r in results),
    }
