def sum_digits(n):
    if n == 0:
        return 1
    return n % 10 + sum_digits(n // 10)
