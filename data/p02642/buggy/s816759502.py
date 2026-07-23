import sys
readline = sys.stdin.readline
sys.setrecursionlimit(10**8)
mod = 10**9+7

INF = 10**18
eps = 10**-7

import itertools

N = int(readline())
A = list(map(int,readline().split()))

A.sort()

from collections import Counter
Ac = Counter(A)
A = []
for k,v in Ac.items():
    if v == 1:
        A.append(k)

check = [[True,False] for i in range(10**6+1)]
ans = 0
for a in A:
    if not check[a][0]:
        continue
    for j in range(2*a,10**6+1,a):
        check[j][0] = False

for a in A:
    if check[a][0]:
        ans += 1
print(ans)

