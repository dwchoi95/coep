MOD = 10 ** 9 + 7
N,M = map(int,input().split())
ans1 = 1
for i in range(N):
    ans1 *= M - i
    ans1 %= MOD
ans2 = [1,M-N]
for i in range(2,N+1):
    ans2.append((ans2[-2] * (N-1) + ans2[-1] * (M-1))% MOD)
print(ans1 * ans2[N] % MOD)