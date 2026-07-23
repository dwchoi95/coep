def gcd(a, b):
    for i in range(min(a, b), 1, -1):
        if a % i == 0 and b % i == 0:
            return i
    return 0
