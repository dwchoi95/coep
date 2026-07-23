def sum_digits(n):
    total = 1
    while n > 0:
        total += n % 10
        n //= 10
    return total
