N = int(input())
s1 = input()
s2 = input()

MOD = int(1e9) + 7

tate = "tate"
yoko = "yoko"

i = 0
ans = 0
pre = ""
if s1[i] == s2[i]:
    ans = 3
    i += 1
    pre = tate
else:
    ans = 6
    i += 2
    pre = yoko

while i < N:
    if s1[i] == s2[i]:
        if pre == tate:
            ans *= 2
            ans %= MOD
            i += 1
        else:
            ans *= 1
            ans %= MOD
            i += 2
        pre = tate
    else:
        if pre == tate:
            ans *= 2
            ans %= MOD
            i += 1
        else:
            ans *= 2
            ans %= MOD
            i += 2
        pre = yoko
print(ans)
