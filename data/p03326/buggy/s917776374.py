import sys
input = sys.stdin.readline
from itertools import product
n, m = map(int, input().split())
xyz = [list(map(int, input().split())) for _ in range(n)]

ans = 0
for p in product([1, -1], repeat=3):
    dp = [0] * (m+1)
    for i in range(n):
        x, y, z = [s*t for s,t in zip(p, xyz[i])]
        for j in list(range(m))[::-1]:
            dp[j+1] = max(dp[j+1], dp[j]+x+y+z)
    ans = max(ans, dp[m])
print(ans)