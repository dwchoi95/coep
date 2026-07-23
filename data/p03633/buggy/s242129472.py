import sys
sys.setrecursionlimit(100000)

N = int(input())
T = []
for i in range(N):
    T.append(int(input()))

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

lcm = 1
for i in T:
    lcm = lcm * i / gcd(lcm, i)

print(lcm)