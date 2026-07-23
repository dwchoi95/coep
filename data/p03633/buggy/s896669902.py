def gcd(a, b):
    while b > 0:
        tmp = a
        a = b
        b = tmp % b
    return a


def lcm(a, b):
    return a*b  


n = int(input())
t = [0 for i in range(n)]
for i in range(n):
    t[i] = int(input())
sum = t[0]
for i in range(1, n):
    
    sum = lcm(sum, t[i])
    
print(sum)
