def gcd(a, b):
    while b > 0:
        tmp = a
        a = b
        b = tmp % b
    return a


def lcm(a, b):
    tmp = gcd(a, b)
    return (a


n = int(input())
t = [0 for i in range(n)]
for i in range(n):
    t[i] = int(input())
t = sorted(t)
_sum = t[0]
for i in range(1, n):
    
    _sum = lcm(_sum, t[i])
    
print(_sum)
