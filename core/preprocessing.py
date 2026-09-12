"""Conservative Indonesian/English sentence extraction for IndoBERT.

Numbers, units, percentages, punctuation, and words are retained. No stemming,
stopword removal, or lowercasing is applied to model input.
"""

from __future__ import annotations

from collections import Counter
import math
import re


MIN_CHAR_LENGTH = 25
_DOT = "\ue000"
_ABBREVIATIONS = re.compile(
    r"\b(?:PT|CV|UD|Tbk|Dr|Dra|Drs|Prof|Ir|Jl|No|Mr|Mrs|Ms|Ltd|Inc|Corp|"
    r"dll|dst|dsb|hlm|hal|vs|etc|Fig|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.",
    re.IGNORECASE,
)
_PAGE_LABEL = re.compile(
    r"^(?:page|halaman|hal\.?|p\.)\s*\d{1,4}(?:\s*(?:/|of|dari)\s*\d{1,4})?$",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Normalize spacing, retaining paragraph boundaries and all meaningful tokens."""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u200b", "").replace("\ufeff", "")
    # Soft hyphens mark optional line wrapping, unlike ordinary lexical hyphens.
    text = re.sub(r"\u00ad\s*\n\s*", "", text).replace("\u00ad", "")
    lines = [re.sub(r"[^\S\n]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _margin_candidate(line: str) -> bool:
    # Avoid treating a repeated complete sentence as a disposable page header.
    return bool(line) and len(line) <= 100 and len(line.split()) <= 12 and not re.search(r"[.!?;]$", line)


def clean_pages(pages: list[dict]) -> list[dict]:
    """Remove obvious page labels and short repeated first/last-line margins.

    Repetition removal needs at least three nonempty pages and a 60% majority.
    Only exact normalized margins are considered; numeric values are not masked.
    """
    prepared = [
        {"page": page["page"], "text": clean_text(page.get("text", ""))}
        for page in pages
    ]
    nonempty = [page for page in prepared if page["text"]]
    margins: Counter[str] = Counter()
    for page in nonempty:
        lines = [line for line in page["text"].splitlines() if line]
        if len(lines) < 2:
            # A page consisting of one repeated claim is not a header/footer.
            continue
        candidates = {lines[0], lines[-1]}
        margins.update(line.casefold() for line in candidates if _margin_candidate(line))
    minimum_repeats = max(3, math.ceil(len(nonempty) * 0.6))
    repeated = {line for line, count in margins.items() if count >= minimum_repeats}
    cleaned: list[dict] = []
    for page in prepared:
        lines = page["text"].splitlines()
        if lines:
            first = next((i for i, line in enumerate(lines) if line), 0)
            last = next((i for i in range(len(lines) - 1, -1, -1) if lines[i]), 0)
            for index in {first, last}:
                line = lines[index]
                bare_page_number = line.strip(" -–—") == str(page["page"])
                is_repeated_margin = first != last and line.casefold() in repeated
                if is_repeated_margin or _PAGE_LABEL.fullmatch(line) or bare_page_number:
                    lines[index] = ""
        cleaned.append({"page": page["page"], "text": clean_text("\n".join(lines))})
    return cleaned


def _protect_dots(text: str) -> str:
    text = re.sub(r"(?<=\d)\.(?=\d)", _DOT, text)
    text = _ABBREVIATIONS.sub(lambda match: match.group().replace(".", _DOT), text)
    text = re.sub(r"\b(?:[A-Za-z]\.){2,}", lambda match: match.group().replace(".", _DOT), text)
    # Preserve dots in URLs/emails but retain terminal sentence punctuation.
    def protect_link(match: re.Match) -> str:
        value = match.group()
        core = value.rstrip(".!?,;:)")
        return core.replace(".", _DOT) + value[len(core):]

    return re.sub(
        r"(?:https?://|www\.)\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        protect_link,
        text,
        flags=re.IGNORECASE,
    )


def segment_claims(text: str, min_char_length: int = MIN_CHAR_LENGTH) -> list[str]:
    """Segment sentences and paragraph/bullet claims, without splitting decimals.

    Single line wraps are joined. Blank lines and explicit bullet starts are
    boundaries. This is a transparent heuristic, not a linguistic claim detector.
    """
    if isinstance(min_char_length, bool) or not isinstance(min_char_length, int) or min_char_length < 1:
        raise ValueError("Panjang minimum klaim harus berupa bilangan bulat positif.")
    normalized = clean_text(text)
    if not normalized:
        return []
    paragraphs = re.split(r"\n\s*\n|\n(?=\s*(?:[•●▪◦]|[-–—]\s|\d{1,3}[.)]\s))", normalized)
    claims: list[str] = []
    for paragraph in paragraphs:
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        if not paragraph:
            continue
        protected = _protect_dots(paragraph)
        # Initial list numbering is punctuation, but does not end a sentence.
        protected = re.sub(r"^(\d{1,3})\.(?=\s)", lambda match: match[1] + _DOT, protected)
        pieces = re.split(r"(?<=[.!?])\s+|(?<=[.!?][\"”’'])\s+", protected)
        for piece in pieces:
            claim = piece.replace(_DOT, ".").strip()
            if len(claim) >= min_char_length and re.search(r"[^\W\d_]", claim, flags=re.UNICODE):
                claims.append(claim)
    return claims


def build_claims(pages: list[dict], min_char_length: int = MIN_CHAR_LENGTH) -> list[dict]:
    """Build stable one-based claim identifiers, retaining the source PDF page."""
    claims: list[dict] = []
    for page in clean_pages(pages):
        for text in segment_claims(page["text"], min_char_length=min_char_length):
            claims.append({"claim_id": len(claims) + 1, "page": page["page"], "text": text})
    return claims
