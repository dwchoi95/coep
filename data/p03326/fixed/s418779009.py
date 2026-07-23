N, M = map(int, input().split())
cake = [list(map(int, input().split())) for _ in range(N)]

INF = 10 ** 18
dp = [[[-INF] * 8 for _ in range(M + 1)] for _ in range(N + 1)]
for i in range(N + 1):
    for msk in range(8):
        dp[i][0][msk] = 0

for i in range(1, N + 1):
    x, y, z = cake[i - 1]
    for j in range(1, M + 1):
        for msk in range(8):
            mx = x * (1 - 2 * (msk >> 2 & 1))
            my = y * (1 - 2 * (msk >> 1 & 1))
            mz = z * (1 - 2 * (msk >> 0 & 1))
            dp[i][j][msk] = max(dp[i - 1][j][msk],
                                dp[i - 1][j - 1][msk] + mx + my + mz)

print(max(dp[N][M][i] for i in range(8)))