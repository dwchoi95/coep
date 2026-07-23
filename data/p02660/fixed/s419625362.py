import math



def is_prime(n):
    if n == 1:
        return 0

    for k in range(2, int(math.sqrt(n)) + 1):
        chk = False
        while (n % k == 0):
            chk = True
            n /= k
            if k not in check:
                check[k] = 1
            else:
                check[k] += 1
        if chk:
            return n
    if n in check:
        return 0
    else:
        check[n] = 1
        return 1


check = {}
n = int(input())
if n == 1:
    print(0)
else:
    while (1):
        n = is_prime(n)
        if n == 0:
            break
    ans = 0
    for k, v in check.items():
        for i in range(1, 50):
            v -= i
            if v < 0:
                break
            else:
                ans += 1
    
    print(ans)
