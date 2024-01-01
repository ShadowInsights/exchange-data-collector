from decimal import Decimal

from app.utilities.math_utils import (calculate_decimal_average,
                                      calculate_decimal_ratio,
                                      calculate_diff_over_sum,
                                      calculate_int_average,
                                      numbers_have_same_sign,
                                      recalculate_round_average, round_to_int)


def test_round_recalc_avg() -> None:
    assert recalculate_round_average(10, 2, 20) == 15
    assert recalculate_round_average(15, 3, 25) == 18
    assert recalculate_round_average(20, 4, 30) == 22


def test_calculate_int_avg() -> None:
    assert calculate_int_average([10, 20, 30], 3) == 20
    assert calculate_int_average([10, 20], 2) == 15
    assert calculate_int_average([10, 20, 30, 40], 4) == 25


def test_calculate_decimal_avg() -> None:
    assert calculate_decimal_average([10.1, 5.9912, 221.231], 3) == Decimal(
        "79.11"
    )
    assert calculate_decimal_average([4.322, 221.57], 2) == Decimal("112.95")
    assert calculate_decimal_average(
        [4.322, 221.57, 32.123, 3121.11], 4
    ) == Decimal("844.78")


def test_numbers_have_same_sign():
    assert numbers_have_same_sign([1, 2, 3]) is True
    assert numbers_have_same_sign([-1, -2, -3]) is True
    assert numbers_have_same_sign([1, -2, 3]) is False
    assert numbers_have_same_sign([-1, 2, -3]) is False
    assert numbers_have_same_sign([]) is True


def test_calculate_diff_over_sum() -> None:
    assert calculate_diff_over_sum(10, 20) == Decimal("-0.33")
    assert calculate_diff_over_sum(0.5, 1.5) == Decimal("-0.5")
    assert calculate_diff_over_sum(25, 15) == Decimal("0.25")


def test_calculate_decimal_ration() -> None:
    assert calculate_decimal_ratio(Decimal("5"), Decimal("2")) == Decimal(
        "2.50"
    )
    assert calculate_decimal_ratio(
        Decimal("123.562"), Decimal("577.11")
    ) == Decimal("0.21")
    assert calculate_decimal_ratio(Decimal("0"), Decimal("2")) == Decimal("0")


def test_decimal_to_int() -> None:
    assert round_to_int(6.7453) == 7
    assert round_to_int(0.2) == 0
    assert round_to_int(4.5) == 5
    assert round_to_int(Decimal(6.7453)) == 7
    assert round_to_int(Decimal(0.2)) == 0
    assert round_to_int(Decimal(4.5)) == 5
