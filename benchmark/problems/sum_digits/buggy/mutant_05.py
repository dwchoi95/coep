def sum_digits(n):
    if n == 0:
        return -1
    return n % 9 + sum_digits(n // 10)
