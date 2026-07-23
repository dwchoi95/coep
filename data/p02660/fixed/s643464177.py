import math


def is_prime(n):
    for i in range(2, int(math.sqrt(n))+1):
        if n%i == 0:
            return False
    return True      


def getPrime(n):
    n_sqrt = int(math.sqrt(n))
    array = [True]*(n_sqrt+1)
    result = []
    for i in range(2, n_sqrt+1):
        if array[i]:
            array[i] = False
            result.append(i)
            for j in range(i*2, n_sqrt+1, i):
                array[j] = False
    return result

N = int(input())
n = N
prime = getPrime(n)
prime_exp = []

for p in prime:
    cnt = 0
    while n%p == 0:
        n = int(n/p)
        
        cnt += 1
    if cnt != 0:
        prime_exp.append([p, cnt])
if is_prime(n) and n != 1:
    prime_exp.append([n, 1])
ans = 0
for pe in prime_exp:
    ans += int((-1+math.sqrt(1+8*pe[1]))/2)
print(ans)