import math

def is_prime(n):
    if n==1:
        return False
    nmax = int(math.sqrt(n)) + 1
    for i in range(2, nmax):
        if(n%i)==0:
            return False
    return True

def pf(n):
    sn = int(math.sqrt(n)) + 1
    ps = []
    for i in range(1, sn):
        if (n%i)==0:
            ps.append(i)
            ps.append(int(n/i))
    del ps[0]
    return ps        

n = int(input())
ps = []
num = pf(n)
for i in num:
    if is_prime(i):
        ps.append(i)
        
zs = []        
for p in ps:
    z = p
    while(z<=n):
        zs.append(z)
        z *= p
zs.sort()

cnt = 0
for z in zs:
    if(n>1):
        if(n%z==0):
            n /= z
            cnt += 1
print(cnt)