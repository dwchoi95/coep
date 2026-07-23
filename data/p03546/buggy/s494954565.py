h,w = map(int,input().split())
ij = [list(map(int,input().split())) for x in range(10)]
dp = [[100 for i in range(10)] for i in range(10)]
for i in range(10):
    dp[i][0] = ij[i][1]
for i in range(1,10):
    for j in range(10):
        num = dp[j][i-1]
        for k in range(10):
            num = min(num,ij[j][k] + dp[k][j-1])
        dp[j][i] = num
ans = 0
for i in range(h):
    for j in list(map(int,input().split())):
        if j == -1:break
        ans += dp[j][-1]
print(ans)