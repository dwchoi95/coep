def gcd(a, b):
    if b == 1:
        return a
    return gcd(b, a % b)
