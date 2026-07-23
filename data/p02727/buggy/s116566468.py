
import sys
import math
import string
import collections
import fractions
import random
from operator import itemgetter
import itertools
from collections import deque
import copy
import heapq
import bisect

MOD = 10 ** 9 + 7
INF = 10 ** 18
input = lambda: sys.stdin.readline().strip()

sys.setrecursionlimit(10 ** 8)

X, Y, A, B, C = map(int, input().split())
p = list(map(int, input().split()))
q = list(map(int, input().split()))
r = list(map(int, input().split()))

p.sort(reverse=True)
q.sort(reverse=True)
r.sort()

ans = sum(p[0:X]) + sum(q[0:Y])

for i in range(C):
    if p[-1] <= q[-1] < r[-1] and A > 0:
        ans += r.pop(-1)
        ans -= p.pop(-1)
        A -= 1
    elif q[-1] <= p[-1] < r[-1] and B > 0:
        ans += r.pop(-1)
        ans -= q.pop(-1)
        B -= 1
    elif q[-1] < r[-1] and B > 0:
        ans += r.pop(-1)
        ans -= q.pop(-1)
        B -= 1
    elif p[-1] < r[-1] and A > 0:
        ans += r.pop(-1)
        ans -= p.pop(-1)
        A -= 1
    else:
        break
print(ans)