
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
mCn = (f[m] * g[m - n] * g[n])

temp1 = (f[n] * f[n - 1])
temp2 = (f[n] * f[n])

if m < 2*n:
    res = (mCn ** 2 * temp1) %mod
else:
    m_nCn = (f[m - n] * g[n] * g[m - 2*n])
    execept = (mCn * m_nCn * temp2)
    res = (execept + ((mCn ** 2 - mCn * m_nCn) * temp1)) %mod
print(res)