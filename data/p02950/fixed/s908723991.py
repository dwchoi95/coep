p = int(input())
mod = p


def frac(limit):
    frac = [1]*limit
    for i in range(2,limit):
        frac[i] = i * frac[i-1]%mod
    fraci = [None]*limit
    fraci[-1] = pow(frac[-1], mod -2, mod)
    for i in range(-2, -limit-1, -1):
        fraci[i] = fraci[i+1] * (limit + i + 1) % mod
    return frac, fraci

frac, fraci = frac(p)



A = list(map(int, input().split()))

C = [0]*p
for i in range(p):
    a = A[i]
    for j in range(i):
        a = (a-C[j]*frac[i]*fraci[i-j])
    C[i] = fraci[i]*a%p
B = [0]*p
t = [0]*p
t[0] = 1
for i in range(p):
    for j in range(p):
        B[j] += t[j]*C[i]
    t2 = ([0] + t)[:-1]
    t2 = [(a-b*i)%p for a, b in zip(t2, t)]
    t = t2[:]

B = [b%p for b in B]
print(*B)