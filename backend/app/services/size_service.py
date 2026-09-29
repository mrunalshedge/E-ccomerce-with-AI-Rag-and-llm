"""Sizes: fit summaries from buyer feedback and size advice from the seller's size chart.

Size charts store *garment* measurements in cm. A garment fits comfortably when it's a bit
bigger than the body ("ease"), e.g. a shirt chest ~6 cm over the body chest. Advice picks the
smallest in-stock size with enough ease everywhere the shopper gave a measurement, then nudges
it by what buyers said ("runs small" → one size up).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.models.review import ReviewFit

CM_PER_INCH = 2.54
MEASUREMENTS = ("chest", "waist", "hip", "length", "shoulder", "sleeve", "inseam")
# Minimum garment-minus-body allowance (cm) for a comfortable fit; others aren't compared.
EASE_CM = {"chest": 6.0, "waist": 4.0, "hip": 6.0}
MIN_FIT_VOTES = 3


def to_cm(value: float, unit: str) -> float:
    return round(value * CM_PER_INCH, 1) if unit == "inch" else float(value)


@dataclass(frozen=True)
class FitSummary:
    runs_small: int
    true_to_size: int
    runs_large: int
    verdict: str | None  # "runs_small" | "true_to_size" | "runs_large" | "mixed" | None (too few votes)

    @property
    def total(self) -> int:
        return self.runs_small + self.true_to_size + self.runs_large


def fit_summary(counts: Mapping[str, int]) -> FitSummary:
    small, true, large = (counts.get(f.value, 0) for f in ReviewFit)
    total = small + true + large
    verdict: str | None = None
    if total >= MIN_FIT_VOTES:
        top, votes = max(((f.value, counts.get(f.value, 0)) for f in ReviewFit), key=lambda x: x[1])
        verdict = top if votes / total >= 0.5 else "mixed"
    return FitSummary(small, true, large, verdict)


@dataclass(frozen=True)
class SizeAdvice:
    size: str | None
    reason: str  # English, factual; the assistant rephrases it in the shopper's language
    checked: list[str]  # which measurements were compared


def recommend_size(
    chart: Sequence[Mapping[str, object]] | None,
    in_stock: Sequence[str],
    body_cm: Mapping[str, float],
    fit_verdict: str | None,
) -> SizeAdvice:
    """``chart`` rows are ordered small → large; ``in_stock`` lists sizes that can be bought."""
    if not chart:
        return SizeAdvice(None, "The seller hasn't provided a size chart for this product.", [])
    rows = [r for r in chart if r.get("size") in in_stock]
    if not rows:
        return SizeAdvice(None, "No sizes are in stock right now.", [])
    compared = [m for m in EASE_CM if m in body_cm and any(isinstance(r.get(m), (int, float)) for r in rows)]
    if not compared:
        return SizeAdvice(None, "Share your chest, waist or hip measurement to get a size suggestion.", [])

    def fits(row: Mapping[str, object]) -> bool:
        return all(
            not isinstance(row.get(m), (int, float)) or float(row[m]) - body_cm[m] >= EASE_CM[m]  # type: ignore[arg-type]
            for m in compared
        )

    index = next((i for i, row in enumerate(rows) if fits(row)), None)
    if index is None:
        largest = rows[-1]["size"]
        return SizeAdvice(str(largest), f"Even the largest size in stock ({largest}) may feel tight.", compared)

    size = str(rows[index]["size"])
    reason = f"{size} gives comfortable room for your {', '.join(compared)}."
    if fit_verdict == "runs_small" and index + 1 < len(rows):
        size = str(rows[index + 1]["size"])
        reason += f" Buyers say it runs small, so {size} is safer."
    elif fit_verdict == "runs_large":
        reason += " Buyers say it runs large; if you prefer a snug fit, one size down may work."
    return SizeAdvice(size, reason, compared)


def validate_sizes(sizes: Sequence[str]) -> None:
    if len(set(s.strip().upper() for s in sizes)) != len(sizes):
        raise ValueError("Each size can only be listed once")


def validate_chart(chart: Sequence[Mapping[str, object]], sizes: Sequence[str]) -> None:
    """Chart rows must refer to the product's sizes and hold plausible cm values."""
    known = set(sizes)
    for row in chart:
        if row.get("size") not in known:
            raise ValueError(f"Size chart row '{row.get('size')}' is not one of the product's sizes")
        for key, value in row.items():
            if key == "size":
                continue
            if key not in MEASUREMENTS:
                raise ValueError(f"Unknown measurement '{key}' (use: {', '.join(MEASUREMENTS)})")
            if not isinstance(value, (int, float)) or not 1 <= float(value) <= 300:
                raise ValueError(f"'{key}' for size {row['size']} must be between 1 and 300 cm")
