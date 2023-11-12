import regex
from _decimal import Decimal

FLOAT_ROUND_REGEX = regex.compile(r"(\.\d*?[1-9])0+$|\.0+$")


def add_comma_every_n_symbols(input_value, n=3) -> str:
    # Ensure the input is a string
    input_str = str(input_value).strip()

    # Split into integer and decimal parts
    if "." in input_str:
        int_part, decimal_part = input_str.split(".")
    else:
        int_part, decimal_part = input_str, None

    # Remove any non-digit characters (like spaces or negative signs) from the integer part
    sign = ""
    if int_part and (int_part[0] == "-" or int_part[0] == "+"):
        sign = int_part[0]  # Save the sign
        int_part = int_part[1:]  # Remove the sign from the integer part

    # Add commas
    reversed_int_part = int_part[::-1]
    commas_added = [
        reversed_int_part[i : i + n]
        for i in range(0, len(reversed_int_part), n)
    ]
    int_with_commas = sign + ",".join(commas_added)[::-1]

    # Combine integer and decimal parts
    if decimal_part is not None:
        return f"{int_with_commas}.{decimal_part}"
    else:
        return int_with_commas


def round_decimal_to_first_non_zero(num: Decimal) -> Decimal:
    str_num = str(num)
    result = FLOAT_ROUND_REGEX.sub(r"\1", str_num)

    return result


def to_title_case(s: str) -> str:
    return s.capitalize()


def replace_char(
    input_str: str, char_to_replace: str, replacement_char: str
) -> str:
    return input_str.replace(char_to_replace, replacement_char)
