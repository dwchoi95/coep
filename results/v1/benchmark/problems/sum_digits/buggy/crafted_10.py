def sum_digits(n):
    while n > 0:
        total = 0
        total += n % 10
        n //= 10
    return total
