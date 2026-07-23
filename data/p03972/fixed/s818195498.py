
from collections import defaultdict,deque
from heapq import heappush, heappop
from bisect import bisect_left, bisect_right
import sys, random, itertools, math
sys.setrecursionlimit(10**5)
input = sys.stdin.readline
sqrt = math.sqrt
def LI(): return list(map(int, input().split()))
def LF(): return list(map(float, input().split()))
def LI_(): return list(map(lambda x: int(x)-1, input().split()))
def II(): return int(input())
def IF(): return float(input())
def LS(): return list(map(list, input().split()))
def S(): return list(input().rstrip())
def IR(n): return [II() for _ in range(n)]
def LIR(n): return [LI() for _ in range(n)]
def FR(n): return [IF() for _ in range(n)]
def LFR(n): return [LI() for _ in range(n)]
def LIR_(n): return [LI_() for _ in range(n)]
def SR(n): return [S() for _ in range(n)]
def LSR(n): return [LS() for _ in range(n)]
mod = 1000000007
inf = 1e10











































































def solve():
    w, h = LI()
    a = []
    x, y = 0, 1
    for _ in range(w):
        a.append((II(), x))
    for _ in range(h):
        a.append((II(), y))
    a.sort()
    plus_x = h + 1
    plus_y = w + 1
    ans = 0
    for ai, xy in a:
        if xy:
            ans += ai * plus_y
            plus_x -= 1
        else:
            ans += ai * plus_x
            plus_y -= 1
    print(ans)
    return



if __name__ == '__main__':
    solve()
