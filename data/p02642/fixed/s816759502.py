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


check = [[False,False] for i in range(10**6+1)]
ans = 0
for a in A:
    if check[a][1]:
        check[a][0] = True
    if check[a][0]:
        continue
    for j in range(2*a,10**6+1,a):
        check[j][0] = True
    check[a][1] = True
 
for a in A:
    if not check[a][0]:
        ans += 1
print(ans)
 