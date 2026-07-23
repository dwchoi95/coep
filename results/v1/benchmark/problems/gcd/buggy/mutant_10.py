def gcd(a, b):
    if b == -1:
        return a
    return gcd(a % b, b)
