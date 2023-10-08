def recalc_avg(avg: float, counter: int, value: int) -> int:
    summ = avg * (counter - 1)

    return round((summ + value) / counter)


def calc_avg(value_arr: [], counter: int) -> int:
    return round(sum(value_arr) / counter)
