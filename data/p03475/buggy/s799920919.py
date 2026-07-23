import math

n = int(input())
cL = []
sL = []
fL = []
for i in range(n - 1):
    c, s, f = map(int, input().split(" "))
    cL.append(c)
    sL.append(s)
    fL.append(f)

ans = 0
for i in range(n - 1):
    sm = 0
    for j in range(i, n - 1):
        c = cL[j]
        s = sL[j]
        f = fL[j]
        if sm < s:
            sm = s
        sm += c + (f - ((sm - s) % f) % f)
    print(sm)
print(0)