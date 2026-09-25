from decimal import Decimal

import pytest

from app.services.pricing import calculate_price_breakdown


def test_standard_breakdown_gst_on_all_fees() -> None:
    p = calculate_price_breakdown("1000", "40", "10", "18")
    assert p.base_price == Decimal("1000.00")
    assert p.taxable_value == Decimal("1050.00")
    assert p.gst_amount == Decimal("189.00")  # 18% of 1050
    assert p.final_price == Decimal("1239.00")
    assert p.currency == "INR"


def test_defaults_are_no_fees_and_18_percent_gst() -> None:
    p = calculate_price_breakdown(Decimal("100"))
    assert p.delivery_fee == Decimal("0.00")
    assert p.platform_fee == Decimal("0.00")
    assert p.gst_percent == Decimal("18.00")
    assert p.final_price == Decimal("118.00")


@pytest.mark.parametrize(
    ("base", "gst", "expected_gst", "expected_final"),
    [
        ("99.99", "18", "18.00", "117.99"),  # 17.9982 rounds up
        ("10.05", "5", "0.50", "10.55"),  # 0.5025 rounds down
        ("0.25", "10", "0.03", "0.28"),  # 0.025 -> half-up, not banker's rounding
        ("499", "0", "0.00", "499.00"),  # GST-exempt goods
    ],
)
def test_rounding_is_half_up_to_two_places(base: str, gst: str, expected_gst: str, expected_final: str) -> None:
    p = calculate_price_breakdown(base, 0, 0, gst)
    assert p.gst_amount == Decimal(expected_gst)
    assert p.final_price == Decimal(expected_final)


@pytest.mark.parametrize("base", ["0.01", "1.005", "333.333", "12345.67", "99999999.99"])
def test_lines_always_sum_to_final_price(base: str) -> None:
    p = calculate_price_breakdown(base, "49.995", "7.5", "12")
    assert p.base_price + p.delivery_fee + p.platform_fee + p.gst_amount == p.final_price
    for amount in (p.base_price, p.delivery_fee, p.platform_fee, p.gst_amount, p.final_price):
        assert amount.as_tuple().exponent == -2


def test_float_input_is_rejected() -> None:
    with pytest.raises(TypeError):
        calculate_price_breakdown(19.99)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_price": "-1"},
        {"base_price": "10", "delivery_fee": "-5"},
        {"base_price": "10", "platform_fee": "-0.01"},
        {"base_price": "10", "gst_percent": "101"},
        {"base_price": "NaN"},
    ],
)
def test_invalid_amounts_raise_value_error(kwargs: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        calculate_price_breakdown(**kwargs)
