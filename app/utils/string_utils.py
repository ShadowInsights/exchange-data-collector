def add_comma_every_n_symbols(input: int, n) -> str:
    if n <= 0:
        return input

    result = []
    reversed_input = str(input)[::-1]  # Reverse the input string

    for i, char in enumerate(reversed_input):
        if i > 0 and i % n == 0:
            result.append(",")
        result.append(char)

    # Reverse the result back to the original order
    result.reverse()

    return "".join(result)
