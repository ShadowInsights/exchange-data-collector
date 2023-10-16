from app.utils.math_utils import calc_avg, calc_round_avg, recalc_round_avg


def test_round_recalc_avg():
    assert recalc_round_avg(10, 2, 20) == 15
    assert recalc_round_avg(15, 3, 25) == 18
    assert recalc_round_avg(20, 4, 30) == 22


def test_round_calc_avg():
    assert calc_round_avg([10, 20, 30], 3) == 20
    assert calc_round_avg([10, 20], 2) == 15
    assert calc_round_avg([10, 20, 30, 40], 4) == 25


def test_calc_avg():
    assert calc_avg([1, 2, 3, 4, 5], 5) == 3.0
    assert calc_avg([-1, -2, 3, 4, 5], 5) == 1.8
    assert calc_avg([-1, -2, -3, -4, -5], 5) == -3.0
