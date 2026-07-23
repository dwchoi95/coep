N, K = map(int, input().split())
m = 1e9+7

dp = [[[0] * (K+2*N+1) for _ in range(N+1)] for _ in range(N+1)]

dp[0][0][0] = 1
for i in range(0, N):
  for j in range(0, i+1):
    for k in range(0, K+1):
      dp[i+1][j+1][k+2*(j+1)] = dp[i+1][j+1][k+2*(j+1)] + dp[i][j][k] % m
      dp[i+1][j][k+2*j] = dp[i+1][j][k+2*j] + dp[i][j][k] % m
      dp[i+1][j][k+2*j] = dp[i+1][j][k+2*j] + 2*j * dp[i][j][k] % m
      if j > 0:
      	dp[i+1][j-1][k+2*(j-1)] = dp[i+1][j-1][k+2*(j-1)] + j*j * dp[i][j][k] % m
print(int(dp[N][0][K]))
