from collections import Counter,defaultdict,deque
from heapq import heappop,heappush,heapify
import sys,bisect,math,itertools,fractions
sys.setrecursionlimit(10**8)
mod = 10**9+7
INF = float('inf')
def inp(): return int(sys.stdin.readline())
def inpl(): return list(map(int, sys.stdin.readline().split()))

def err():
    print(0)
    quit()

n = inp()
a = inpl()
b = inpl()
if a[-1] != b[0]: err()
de = [-1] * n
mx = [INF] * n
now = -1
for i in range(n):
    if a[i] > now:
        now = a[i]
        de[i] = now
    else:
        mx[i] = now
now = -1
for i in range(n)[::-1]:
    if b[i] > now:
        now = b[i]
        if de[i] != -1 and de[i] != now:
            err()
        de[i] = now
    else:
        if now < de[i]: err()
        mx[i] = min(mx[i], now)
res = 1
for i in range(n):
    if de[i] == -1:
        res *= mx[i]
        res %= mod
print(res)