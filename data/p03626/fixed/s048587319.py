n = int(input())
s1 = input()
s2 = input()

mod = 10**9+7

if s1[0] == s2[0]:
    ans = 3
    bfr = 'T'
    idx = 1
else:
    ans = 6
    bfr = 'Y'
    idx = 2

if n == 1:
    print(ans)
    exit()

while idx <= n-1:
    if s1[idx] == s2[idx]:
        if bfr == 'T':
            ans *= 2
            ans %= mod
        idx += 1
        bfr = 'T'
    else:
        if bfr == 'T':
            ans *= 2
            ans %= mod
        else:
            ans *= 3
            ans %= mod
        idx += 2
        bfr = 'Y'
        
print(ans%mod)