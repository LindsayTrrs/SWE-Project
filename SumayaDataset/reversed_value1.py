value = 2025
start_value = value
reversed_value = 0

while value != 0:
    last_digit = value % 4
    shifted = reversed_value * 4
    reversed_value = shifted + last_digit
    value = value // 4
