"""Transparent downstream risk aggregation; never substitutes for model inference."""

from __future__ import annotations

import math

from core.settings import DEFAULT_THRESHOLD


POSITIVE_LABEL = "Higher Evidentiary Risk"
NEGATIVE_LABEL = "Lower Evidentiary Risk"


def _validate_threshold(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} harus berada di antara 0 dan 1.")
    return value


def apply_threshold(results: list[dict], threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    """Reclassify cached softmax probabilities without mutating input or using a model.

    Confidence is the softmax probability of the threshold-selected class; at a
    custom threshold this can be below 0.5. A tie at the threshold is positive.
    Preserve the original negative-class softmax value when supplied: float32
    softmax values may sum only approximately to one. Probability-only inputs
    retain the binary-complement fallback for compatibility.
    """
    threshold = _validate_threshold(threshold, "Threshold")
    output: list[dict] = []
    for result in results:
        probability = _validate_threshold(result["greenwashing_probability"], "Probabilitas")
        low_probability = 1.0 - probability
        class_probabilities = result.get("probabilities")
        if class_probabilities is not None:
            if not isinstance(class_probabilities, dict):
                raise ValueError("Probabilitas per kelas harus berupa mapping label dan nilai.")
            if NEGATIVE_LABEL in class_probabilities:
                low_probability = _validate_threshold(
                    class_probabilities[NEGATIVE_LABEL], "Probabilitas Lower Evidentiary Risk"
                )
                if not math.isclose(probability + low_probability, 1.0, rel_tol=0.0, abs_tol=1e-5):
                    raise ValueError("Probabilitas kedua kelas tidak konsisten: jumlahnya harus mendekati 1.")
        flagged = probability >= threshold
        output.append(
            {
                **result,
                "prediction": POSITIVE_LABEL if flagged else NEGATIVE_LABEL,
                "greenwashing_probability": probability,
                "confidence": probability if flagged else low_probability,
            }
        )
    return output


def calculate_document_risk(
    results: list[dict], threshold: float = DEFAULT_THRESHOLD, high_confidence_threshold: float = 0.8
) -> dict:
    """Aggregate real claim probabilities using the documented v1 formula.

    Risk = 100 * (0.50 * mean_probability + 0.35 * flagged_ratio
                  + 0.15 * high_confidence_flagged_ratio).

    Both ratios use ALL analyzed claims as their denominator. A high-confidence
    flag must satisfy both the current classification threshold and the
    high-confidence threshold. Continuous scores use <=30 LOW, <=60 MODERATE,
    >60 HIGH, avoiding gaps at fractional values such as 30.5 or 60.5. The index
    is an aggregation heuristic, not a probability or a class learned by IndoBERT.
    """
    threshold = _validate_threshold(threshold, "Threshold")
    high_confidence_threshold = _validate_threshold(high_confidence_threshold, "High confidence threshold")
    if not results:
        raise ValueError("Tidak ada klaim yang dapat digunakan untuk menghitung Risk Index.")
    classified = apply_threshold(results, threshold)
    total = len(classified)
    flagged = sum(row["prediction"] == POSITIVE_LABEL for row in classified)
    high_confidence = sum(
        row["prediction"] == POSITIVE_LABEL
        and row["greenwashing_probability"] >= high_confidence_threshold
        for row in classified
    )
    mean_probability = math.fsum(row["greenwashing_probability"] for row in classified) / total
    flagged_ratio = flagged / total
    high_confidence_ratio = high_confidence / total
    risk_score = 100.0 * (0.50 * mean_probability + 0.35 * flagged_ratio + 0.15 * high_confidence_ratio)
    risk_score = min(100.0, max(0.0, risk_score))
    risk_level = "LOW" if risk_score <= 30 else "MODERATE" if risk_score <= 60 else "HIGH"
    return {
        "total_claims": total,
        "flagged_claims": flagged,
        "flagged_ratio": flagged_ratio,
        "mean_greenwashing_probability": mean_probability,
        "high_confidence_flagged_ratio": high_confidence_ratio,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "threshold": threshold,
        "high_confidence_threshold": high_confidence_threshold,
    }
