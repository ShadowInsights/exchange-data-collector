from decimal import ROUND_HALF_UP, Decimal
from typing import List, Union

DECIMAL_ROUND_EXAMPLE = Decimal("1.00")


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


def calculate_decimal_ratio(divisible: Decimal, divider: Decimal) -> Decimal:
    assert divider != 0

    ratio = divisible / divider

    return ratio.quantize(DECIMAL_ROUND_EXAMPLE, ROUND_HALF_UP)


def calculate_decimal_average(value_arr: list[float], counter: int) -> Decimal:
    assert counter != 0

    summary = Decimal(sum(value_arr)) / counter

    return summary.quantize(DECIMAL_ROUND_EXAMPLE, ROUND_HALF_UP)


def calculate_int_average(value_arr: list[int], counter: int) -> int:
    assert counter != 0

    return round(sum(value_arr) / counter)


def calculate_avg_by_summary(summary: int, counter: int) -> int:
    assert counter != 0

    return round(summary / counter)


def numbers_have_same_sign(numbers: List[Union[int, float, Decimal]]) -> bool:
    if not numbers:
        return True
    return all(n >= 0 for n in numbers) or all(n < 0 for n in numbers)


def calculate_diff_over_sum(diminished: float, subtrahend: float) -> Decimal:
    assert diminished != 0 and subtrahend != 0

    return Decimal(
        (diminished - subtrahend) / (diminished + subtrahend)
    ).quantize(DECIMAL_ROUND_EXAMPLE, ROUND_HALF_UP)


def round_to_int(number: Decimal | float) -> int:
    if isinstance(number, float):
        return int(Decimal(number).to_integral_value(ROUND_HALF_UP))

    if isinstance(number, Decimal):
        return int(number.to_integral_value(ROUND_HALF_UP))
