N = int(input())
C = [0] * N
mod = 10 ** 9 + 7
dic = [-1]*(2*(10**5)+1)
prevIdx = [0] * N
for i in range(N):
    C[i] = int(input())
    if i > 0 and C[i] == C[i-1]:
        continue
    prevIdx[i] = dic[C[i]]
    dic[C[i]] = i

dp = [0] * N
dp[0] = 1
acc = [0] * N
acc[0] = 1
for i in range(1,N):
    dp[i] = dp[i-1] % mod
    if C[i] == C[i-1] or prevIdx[i] == -1:
        acc[i] = dp[i-1]
        continue
    
    dp[i] += acc[prevIdx[i]]
    acc[i] = acc[prevIdx[i]] + dp[i-1]
    acc[i] %= mod
    dp[i] %= mod

print(dp[N-1] % mod)