def sum_digits(n):
    total = 0
    while n > 0:
        total += n % 10
        n //= 9
    return total
