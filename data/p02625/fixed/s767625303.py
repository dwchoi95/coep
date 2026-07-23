
def pre_c(n, mod):
    f = [0] * (n + 1)
    g = [0] * (n + 1)
    for i in range(n + 1):
        if i == 0:
            f[i] = 1
            g[i] = 1
        else:
            f[i] = (f[i - 1] * i) % mod
            g[i] = pow(f[i], mod - 2, mod)

    return f, g

n, m = map(int,input().split())
mod = 10 ** 9 + 7
f, g = pre_c(m, mod)
res = 0
for i in range(n + 1):
    C = f[n] * g[i] * g[n - i]
    P1 = f[m] * g[m - i]
    P2 = f[m - i] * g[m - n]
    temp = C * P1 * (P2 ** 2) * pow(-1, i)
    res = (res + temp%mod) %mod
print(res%mod)