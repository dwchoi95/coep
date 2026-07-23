import math
data = input()
target = int(data)

def primes(n):
    is_prime = [True] * (n + 1)
    is_prime[0] = False
    is_prime[1] = False
    for i in range(2, int(n**0.5) + 1):
        if not is_prime[i]:
            continue
        for j in range(i * 2, n + 1, i):
            is_prime[j] = False
    return [i for i in range(n + 1) if is_prime[i]]

list = primes(2000000)
result =[]
for i in list:
    check = target
    k = 0
    while True:
        if check % i != 0:
            break
        else:
            check = check/i
            k +=1
    result.append(k)

ans = 0
for j in result:
    y = 0
    z = j
    while z > y:
        y += 1
        z -= y
        ans += 1


cover = 1
for i in range(len(list)):
    cover = cover*(list[i]**result[i])
if target/cover >2000000:
    ans +=1
print(ans)