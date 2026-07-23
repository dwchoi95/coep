def gcd(a, b):
    if a == 0:
        return b
    r = b % a
    return gcd(r, b)
