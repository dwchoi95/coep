import math, string, itertools, fractions, heapq, collections, re,  array, bisect, sys, random, time, copy, functools
sys.setrecursionlimit(10**7)
inf = 10 ** 20
eps = 1.0 / 10**10
mod = 10**9+7
dd = [(-1, 0), (0, 1), (1, 0), (0, -1)]
ddn = [(-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1)]
def LI(): return [int(x) for x in sys.stdin.readline().split()]
def LI_(): return [int(x)-1 for x in sys.stdin.readline().split()]
def LF(): return [float(x) for x in sys.stdin.readline().split()]
def LS(): return sys.stdin.readline().split()
def I(): return int(sys.stdin.readline())
def F(): return float(sys.stdin.readline())
def pf(s): return print(s, flush=True)

N=I()
A=LI()
B = []
counts = collections.Counter(A)
for count in counts.items():
    if count[1] >= 2:
        B.append(count)
B.sort(reverse=True)
if len(B) ==0:
    print(0)
elif len(B) == 1:
    if B[0][1] >= 4:
        print(B[0][0]**2)
    else:
        print(0)
else:
    if B[0][1] >= 4:
        print(B[0][0]**2)
    else:
        print(B[0][0]*B[1][0])
    