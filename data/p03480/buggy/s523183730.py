
from collections import defaultdict
from collections import deque
from heapq import heappush, heappop
import sys
import math
import bisect
import random
import itertools
sys.setrecursionlimit(10**5)
stdin = sys.stdin
bisect_left = bisect.bisect_left
bisect_right = bisect.bisect_right
def LI(): return list(map(int, stdin.readline().split()))
def LF(): return list(map(float, stdin.readline().split()))
def LI_(): return list(map(lambda x: int(x)-1, stdin.readline().split()))
def II(): return int(stdin.readline())
def IF(): return float(stdin.readline())
def LS(): return list(map(list, stdin.readline().split()))
def S(): return list(stdin.readline().rstrip())
def IR(n): return [II() for _ in range(n)]
def LIR(n): return [LI() for _ in range(n)]
def FR(n): return [IF() for _ in range(n)]
def LFR(n): return [LI() for _ in range(n)]
def LIR_(n): return [LI_() for _ in range(n)]
def SR(n): return [S() for _ in range(n)]
def LSR(n): return [LS() for _ in range(n)]
mod = 1000000007
inf = float('INF')


def A():
    a, b, c, d = LI()
    a += b
    c += d
    ans = ["Left", "Right"]
    if a == c:
        print("Balanced")
        return
    print(ans[a < c])
    return


def B():
    n, a, b = LI()
    ans = 0
    for i in range(1, n + 1):
        if a <= sum(list(map(int, list(str(i))))) <= b:
           ans += i
    print(ans) 
    
    return


def C():
    x, y = LI()
    ans = 0
    while x <= y:
        ans += 1
        x *= 2
    print(ans)
    return





def D():
    s = S()
    ans = inf
    n = len(s)
    for i in range(n - 1):
        if s[i] != s[i + 1]:
            ans = min(ans, max(i + 1, n - i - 1))
    print(ans if ans != inf else 0)
    return


if __name__ == '__main__':
    D()
