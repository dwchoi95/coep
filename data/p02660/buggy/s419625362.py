import math



def is_prime(n):
    if n == 1:
        return 0

    for k in range(2, int(math.sqrt(n)) + 1):
        if n % k == 0:
            if k not in check:
                check[k] = 0
                return n / k
            else:
                continue
    if n in check:
        return 0
    else:
        return 1


check = {}
n = int(input())
if n == 1:
    print(0)
else:
    ans = 0
    while (1):
        n = is_prime(n)
        if n == 0:
            break
        else:
            ans += 1
    print(ans)
