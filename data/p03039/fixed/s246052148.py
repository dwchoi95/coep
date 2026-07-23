from math import factorial
N, M, K = map(int, input().split())

MOD = 10**9+7

fact = [1] * (N*M+1)
for i in range(2, N*M+1):
    fact[i] = fact[i-1] * i % MOD

def comb(n, r):
    r = n-r if n-r < r else r
    return fact[n] * pow(fact[r], MOD-2, MOD) * pow(fact[n-r], MOD-2, MOD) % MOD

p = comb(N*M-2, K-2)
ans = 0
for i in range(N):
    for j in range(M):
        if i == 0 and j == 0:
            continue
        d = i+j
        cnt = (N-i) * (M-j)
        if i != 0 and j != 0:
            cnt *= 2
        ans += d * cnt % MOD
ans = ans * p % MOD

print(ans)
