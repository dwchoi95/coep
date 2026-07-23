import sys
N = int(input())
C = [0]
n = N
for i in range(1, n + 1):
    c = int(sys.stdin.readline())
    if c == C[-1]:
        N -= 1
    else:
        C.append(c)
dp = [0] * (N + 2)
dp[0] = 1
dp[1] = 1
cumsum = [0] * (2 * (10 ** 5) + 2)
cumsum[C[1]] = 1
for i in range(2, N+1):
    dp[i] = dp[i - 1] + cumsum[C[i]]
    cumsum[C[i]] += dp[i-1]
    dp[i] %= (10 ** 9 + 7)
print(dp[N])
