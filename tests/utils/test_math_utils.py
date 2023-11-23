from _decimal import Decimal

from app.utils.math_utils import (
    calculate_diff_over_sum,
    calculate_round_avg,
    recalculate_round_average,
    round_to_int,
)


def test_round_recalc_avg() -> None:
    assert recalculate_round_average(10, 2, 20) == 15
    assert recalculate_round_average(15, 3, 25) == 18
    assert recalculate_round_average(20, 4, 30) == 22


def test_round_calc_avg() -> None:
    assert calculate_round_avg([10, 20, 30], 3) == 20
    assert calculate_round_avg([10, 20], 2) == 15
    assert calculate_round_avg([10, 20, 30, 40], 4) == 25


def test_calculate_diff_over_sum() -> None:
    assert calculate_diff_over_sum(10, 20) == -0.33
    assert calculate_diff_over_sum(0.5, 1.5) == -0.5
    assert calculate_diff_over_sum(25, 15) == 0.25


def test_decimal_to_int() -> None:
    assert round_to_int(6.7453) == 7
    assert round_to_int(0.2) == 0
    assert round_to_int(4.5) == 5
    assert round_to_int(Decimal(6.7453)) == 7
    assert round_to_int(Decimal(0.2)) == 0
    assert round_to_int(Decimal(4.5)) == 5
