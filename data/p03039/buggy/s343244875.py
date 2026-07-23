N, M, K = map(int, input().split())

MOD = 10**9+7

def comb(n, r):
    r = n-r if n-r < r else r
    if r == 0:
        return 1
    ndfact = 1
    for i in range(n, n-r, -1):
        ndfact *= i
        ndfact %= MOD
    rfact = 1
    for i in range(r, 1, -1):
        rfact *= i
        rfact %= MOD
    return ndfact 

p = comb(N*M-2, K-2) % MOD
ans = 0
for i in range(N):
    for j in range(M):
        if i == 0 and j == 0:
            continue
        d = i+j
        cnt = (N-i) * (M-j)
        if i != 0 and j != 0:
            cnt *= 2
        ans += d * cnt
        ans %= MOD

print((ans*p)%MOD)
