n = int(input())
c = [int(input()) for _i in range(n)]

dic = {}
dp = [0 for _i in range(n)]
dp[0] = 1
for i in range(1, n):
    if c[i-1] != c[i]:
        if c[i] in dic:
            dp[i] += dic[c[i]]
            dic[c[i]] += dp[i-1]
        else:
            dic[c[i]] = dp[i-1] + 1
    dp[i] += dp[i-1]
print(dp[n-1])