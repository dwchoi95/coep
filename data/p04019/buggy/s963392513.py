from collections import Counter,defaultdict,deque
from heapq import heappop,heappush,heapify
import sys,bisect,math,itertools
sys.setrecursionlimit(10**8)
mod = 10**9+7
mod2 = 998244353
INF = float('inf')
def inp(): return int(sys.stdin.readline())
def inpl(): return list(map(int, sys.stdin.readline().split()))
def inpln(n): return list(int(sys.stdin.readline()) for i in range(n))

s = input()
n = len(s)
u = 0
l = 0
for i in s:
    if i == 'N':
        u += 1
    elif i == 'S':
        u -= 1
    elif i == 'E':
        l += 1
    else:
        l -= 1
    if u == 0 and l == 0:
        print('Yes')
        break
else:
    print('No')

    