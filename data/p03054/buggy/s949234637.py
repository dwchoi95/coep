


import sys
import math
from bisect import bisect_right as br
from bisect import bisect_left as bl
sys.setrecursionlimit(1000000000)
from heapq import heappush, heappop,heappushpop
from collections import defaultdict
from itertools import accumulate
from collections import Counter
from collections import deque
from operator import itemgetter
from itertools import permutations
mod = 10**9 + 7
inf = float('inf')
def I(): return int(sys.stdin.readline())
def LI(): return list(map(int,sys.stdin.readline().split()))

h,w,n = LI()
sr,sc = LI()
sr -= 1
sc -= 1
h -= 1
w -= 1
s = input()
t = input()
l,r,d,u = 0,w,h,0
for i in range(n)[::-1]:
    if t[i] == 'R':
        if l > 0:
            l -= 1
    elif t[i] == 'L':
        if r < w:
            r += 1
    elif t[i] == 'U':
        if u < h:
            d -= 1
    elif t[i] == 'D':
        if d > 0:
            u += 1
    if s[i] == 'R':
        r -= 1
        if r < 0:
            print('NO')
            quit()
    elif s[i] == 'L':
        l += 1
        if l > w:
            print('NO')
            quit()
    elif s[i] == 'U':
        u += 1
        if u > h:
            print('NO')
            quit()
    elif s[i] == 'D':
        d -= 1
        if d < 0:
            print('NO')
            quit()
    
if l <= sc <= r and u <= sr <= d:
    print('YES')
else:
    print('NO')
            