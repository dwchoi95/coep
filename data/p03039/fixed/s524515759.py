MOD = 10 ** 9 + 7


def prepare(n):
    global MOD
    modFacts = [0] * (n + 1)
    modFacts[0] = 1
    for i in range(n):
        modFacts[i + 1] = (modFacts[i] * (i + 1)) % MOD

    invs = [1] * (n + 1)
    invs[n] = pow(modFacts[n], MOD - 2, MOD)
    for i in range(n, 1, -1):
        invs[i - 1] = (invs[i] * i) % MOD

    return modFacts, invs


def modCombi(n, r):
    global MOD
    return (modFacts[n] * invs[n - r] * invs[r]) % MOD


N, M, K = map(int, input().split())
modFacts, invs = prepare(N * M)
var = modCombi(N * M - 2, K - 2)

ans = 0
if N < M:
    N, M = M, N
L = [0] * (N + 1)
for i in range(1, N + 1):
    L[i] = L[i - 1] + i
for x in range(1, N + 1):
    for y in range(1, M + 1):
        Sx = (M * (L[N - x] + L[x - 1])) % MOD
        Sy = (N * (L[M - y] + L[y - 1])) % MOD
        ans += (Sx + Sy) % MOD

print((ans * invs[2] * var) % MOD)

