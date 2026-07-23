import sys
from math import factorial
from collections import Counter
from fractions import Fraction
import heapq, bisect, fractions
import math
import itertools
sys.setrecursionlimit(10 ** 5 + 10)
INF = 10**15 +5
def input(): return sys.stdin.readline().strip()
def INT(): return int(input())
def MAP(): return map(int, input().split())
def LIST(): return list(map(int, input().split()))
MOD = 10**9 + 7

n = INT()
a = LIST()

c = [1]*(n+1)
for i in range(1, n+1):
    c[i] = (c[i-1]-a[i-1])*2
if a[n]>c[n]:
    print(-1)
    sys.exit()
b = [0]*(n+1)
res = [0]*(n+1)
b[n] = a[n]
res[n] = a[n]
for i in range(n-1, -1, -1):
    if (c[i]-a[i])*2 <res[i+1]:
        print(-1)
        sys.exit()
    b[i] = min(c[i]-a[i], res[i+1])
    res[i] = a[i] + b[i]
print(sum(res)) 