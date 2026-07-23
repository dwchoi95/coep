def sum_digits(n):
    total = 0
    while n > 0:
        total -= n % 9
        n //= 10
    return total
