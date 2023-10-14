from decimal import Decimal

import regex

DECIMAL_ROUND_REGEX = regex.compile(r"(\.\d*?[1-9])0+$|\.0+$")


def add_comma_every_n_symbols(
    input: [int, float, str, Decimal], n: int = 3
) -> str:
    if n <= 0:
        return str(input)

    input_str = str(input)
    if "." in input_str:
        int_part, decimal_part = input_str.split(".")
    else:
        int_part = input_str
        decimal_part = None

    result = []
    reversed_int = int_part[::-1]

    for i, char in enumerate(reversed_int):
        if i > 0 and i % n == 0:
            result.append(",")
        result.append(char)

    result.reverse()

    if decimal_part:
        return "".join(result) + "." + decimal_part
    else:
        return "".join(result)


def round_decimal_to_first_non_zero(num: Decimal) -> Decimal:
    str_num = str(num)
    result = DECIMAL_ROUND_REGEX.sub(r"\1", str_num)

    return result
