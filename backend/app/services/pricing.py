"""The single source of truth for product prices.

Rule: GST is charged on the whole taxable value (base + delivery + platform fee), as Indian
marketplaces do. Every line is rounded to 2 places (ROUND_HALF_UP) *before* summing, so the
lines a customer sees always add up exactly to the final price.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.schemas.pricing import PriceBreakdown

MONEY_QUANTUM = Decimal("0.01")
DEFAULT_GST_PERCENT = Decimal("18")

MoneyInput = Decimal | int | str


def _to_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _to_decimal(value: MoneyInput, field: str) -> Decimal:
    # Floats can't represent most decimal amounts exactly (0.1 + 0.2 != 0.3), so refuse them.
    if isinstance(value, float):
        raise TypeError(f"{field} must be Decimal, int or str, not float")
    result = value if isinstance(value, Decimal) else Decimal(value)
    if not result.is_finite():
        raise ValueError(f"{field} must be a finite number")
    if result < 0:
        raise ValueError(f"{field} cannot be negative")
    return result


def calculate_price_breakdown(
    base_price: MoneyInput,
    delivery_fee: MoneyInput = 0,
    platform_fee: MoneyInput = 0,
    gst_percent: MoneyInput = DEFAULT_GST_PERCENT,
) -> PriceBreakdown:
    base = _to_money(_to_decimal(base_price, "base_price"))
    delivery = _to_money(_to_decimal(delivery_fee, "delivery_fee"))
    platform = _to_money(_to_decimal(platform_fee, "platform_fee"))
    gst_rate = _to_decimal(gst_percent, "gst_percent")
    if gst_rate > 100:
        raise ValueError("gst_percent cannot exceed 100")

    taxable = base + delivery + platform
    gst_amount = _to_money(taxable * gst_rate / Decimal(100))

    return PriceBreakdown(
        base_price=base,
        delivery_fee=delivery,
        platform_fee=platform,
        taxable_value=taxable,
        gst_percent=_to_money(gst_rate),
        gst_amount=gst_amount,
        final_price=taxable + gst_amount,
    )
