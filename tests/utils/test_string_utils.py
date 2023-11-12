from decimal import Decimal

from app.utils.string_utils import (
    add_comma_every_n_symbols,
    round_decimal_to_first_non_zero,
    to_title_case,
)


def test_add_comma_every_n_symbols():
    assert add_comma_every_n_symbols(1000) == "1,000"
    assert add_comma_every_n_symbols(1000.01) == "1,000.01"
    assert add_comma_every_n_symbols(1000, 4) == "1000"
    assert add_comma_every_n_symbols(10000, 4) == "1,0000"
    assert add_comma_every_n_symbols(10000.5678, 4) == "1,0000.5678"
    assert add_comma_every_n_symbols("1000000", 2) == "1,00,00,00"
    assert add_comma_every_n_symbols(Decimal("100000.123"), 3) == "100,000.123"
    assert add_comma_every_n_symbols(Decimal("204170.52")) == "204,170.52"
    assert (
        add_comma_every_n_symbols(f"{Decimal(314378.4376000000000000): .2f}")
        == "314,378.44"
    )


def test_round_decimal_to_first_non_zero():
    assert round_decimal_to_first_non_zero(Decimal("1.100")) == "1.1"
    assert round_decimal_to_first_non_zero(Decimal("1.12000")) == "1.12"
    assert round_decimal_to_first_non_zero(Decimal("1.0")) == "1"


def test_to_title_case():
    assert to_title_case("hello") == "Hello"
    assert to_title_case("HELLO") == "Hello"
    assert to_title_case("hELLo") == "Hello"
    assert to_title_case("") == ""
