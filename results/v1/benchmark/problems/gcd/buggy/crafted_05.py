def gcd(a, b):
    best = 1
    for i in range(1, min(a, b)):
        if a % i == 0 and b % i == 0:
            best = i
    return best
