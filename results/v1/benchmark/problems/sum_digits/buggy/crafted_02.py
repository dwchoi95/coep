def sum_digits(n):
    s = str(n)
    total = 0
    for i in range(len(s) - 1):
        total += int(s[i])
    return total
