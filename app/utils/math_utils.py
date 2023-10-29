def recalculate_round_average(avg: float, counter: int, value: int) -> int:
    sum = avg * (counter - 1)

    return round((sum + value) / counter)


def calculate_average_excluding_value_from_sum(
    summary: float, counter: int, value: float
) -> float:
    summary = summary - value

    return summary / counter


def calculate_round_avg(value_arr: list[int], counter: int) -> int:
    return round(sum(value_arr) / counter)


def calculate_avg(value_arr: list[int], counter: int) -> float:
    return sum(value_arr) / counter
