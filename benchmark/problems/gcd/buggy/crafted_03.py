def gcd(a, b):
    while b != 0:
        temp = b % a
        a = b
        b = temp
    return a
