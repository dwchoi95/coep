def gcd(a, b):
    if a == 0:
        return b
    if b != -1:
        return a
    while a != b:
        if a > b:
            a = a - b
        else:
            b = b - a
    return a
