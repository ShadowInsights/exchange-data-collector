from app.utils.math_utils import (calculate_diff_over_sum, calculate_round_avg,
                                  recalculate_round_average)


def test_round_recalc_avg():
    assert recalculate_round_average(10, 2, 20) == 15
    assert recalculate_round_average(15, 3, 25) == 18
    assert recalculate_round_average(20, 4, 30) == 22


def test_round_calc_avg():
    assert calculate_round_avg([10, 20, 30], 3) == 20
    assert calculate_round_avg([10, 20], 2) == 15
    assert calculate_round_avg([10, 20, 30, 40], 4) == 25


def test_calculate_diff_over_sum():
    assert calculate_diff_over_sum(10, 20) == -0.33
    assert calculate_diff_over_sum(0.5, 1.5) == -0.5
    assert calculate_diff_over_sum(25, 15) == 0.25
