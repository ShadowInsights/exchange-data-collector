from _decimal import ROUND_HALF_UP, Decimal


def recalculate_round_average(avg: float, counter: int, value: int) -> int:
    assert counter != 0

    sum = avg * (counter - 1)

    return round((sum + value) / counter)


def calculate_average_excluding_value_from_sum(
    summary: Decimal, counter: int, value: Decimal
) -> Decimal:
    assert counter != 0

    summary = summary - value

    return summary / counter


def calculate_round_avg(value_arr: list[int], counter: int) -> int:
    assert counter != 0

    return round(sum(value_arr) / counter)


def calculate_avg_by_summary(summary: int, counter: int) -> int:
    assert counter != 0

    return round(summary / counter)


def calculate_diff_over_sum(diminished: float, subtrahend: float) -> float:
    assert diminished != 0 and subtrahend != 0

    return round((diminished - subtrahend) / (diminished + subtrahend), 2)


def round_to_int(number: Decimal | float) -> int:
    if isinstance(number, float):
        return int(Decimal(number).to_integral_value(ROUND_HALF_UP))

    if isinstance(number, Decimal):
        return int(number.to_integral_value(ROUND_HALF_UP))
