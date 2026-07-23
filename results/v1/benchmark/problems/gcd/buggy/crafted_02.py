def gcd(a, b):
    if b == 0:
        return 0
    r = a % b
    return gcd(b, r)
