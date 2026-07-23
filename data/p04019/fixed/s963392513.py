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
c = Counter(s)
a,b,c,d = [c['N'], c['S'], c['W'], c['E']]
if (a and b) or (not a and not b):
    if (c and d) or (not c and not d):
        print('Yes')
        quit()
print('No')