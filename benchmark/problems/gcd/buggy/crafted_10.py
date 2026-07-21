def gcd(a, b):
    while a % b != 0:
        temp = b
        b = a % b
        a = temp
    return b
