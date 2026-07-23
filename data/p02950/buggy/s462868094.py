p = int(input())
a = list(map(int, input().split()))
MOD = p

P = p
fact = [0] * P
fact[0] = 1
for i in range(1, P):
    fact[i] = fact[i - 1] * i
    fact[i] %= MOD

rfact = [0] * P
rfact[P - 1] = pow(fact[P - 1], MOD - 2, MOD)
for i in range(P - 2, -1, -1):
    rfact[i] = rfact[i + 1] * (i + 1)
    rfact[i] %= MOD


def comb(n, k):
    return fact[n] * rfact[n - k] * rfact[k] % MOD


b = [0] * p
for i in range(p):
    if a[i]:
        b[0] += 1
        b[0] %= MOD
        s = 1
        for j in range(p):
            b[j] -= comb(p - 1, j) * s
            b[j] %= MOD
            s *= -i
            s %= MOD

print(*b)