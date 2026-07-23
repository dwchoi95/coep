from collections import Counter
n = int(input())
ans = 0
def primes(n):
    is_p = [True]*(n + 1)
    is_p[0] = False
    is_p[1] = False
    for i in range(2, int(n**0.5)+1):
        if not is_p[i]:
            continue
        for j in range(i*2, n+1, i):
            is_p[j] = False
    return [i for i in range(n+1) if is_p[i]]

p = primes(10**6)

dp = []
cl = []
n1 = n
for i in p:
    if n%i == 0:
        cl.append(i)
    while n%i == 0:
        n = n/i
        dp.append(i)
    if n == 1:
        break
if n == n1:
    dp.append(n)
    cl.append(n)

c = Counter(dp)

for i in cl:
    cnt = 1
    while c[i] >= cnt:
        c[i] -= cnt
        ans += 1
        cnt += 1
        
print(ans)
