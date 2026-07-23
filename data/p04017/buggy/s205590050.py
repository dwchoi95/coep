import sys
input = sys.stdin.readline

from bisect import bisect

n = int(input())
x = list(map(int, input().split()))
l = int(input())

m = 20
par = [[-1]*n for i in range(m)]

for i in range(n-1):
    j = bisect(x, x[i]+l)-1
    par[0][i] = j

for i in range(m-1):
    for j in range(n):
        par[i+1][j]=par[i][par[i][j]]

def hoge(x, y):
    k = 0
    for i in range(m)[::-1]:
        if 0 <= par[i][x] <= y:
            k += 1<<i
            x = par[i][x]
    return k

q = int(input())
ans = []
for i in range(q):
    a,b = map(int, input().split())
    a,b = a-1,b-1
    if a > b:
        a,b = b,a
    ans.append(hoge(a, b))

print(*ans, sep="\n")