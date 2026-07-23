import collections

h, w, m = map(int, input().split())
lsh = [0] * h
lsw = [0] * w

bom = []
for _ in range(m):
    m1, m2 = map(int, input().split())
    lsh[m1 - 1] += 1
    lsw[m2 - 1] += 1
    bom.append((m1-1, m2-1))

lshmax = max(lsh)
lswmax = max(lsw)
hin = [i for i in lsh if i == lshmax]
win = [i for i in lsw if i == lswmax]


jd= False

for i in hin:
    for j in win:
        if (i, j) not in bom:
                    jd= True
                    
if jd:
    print(lshmax+lswmax)
else:
    print(lshmax + lswmax -1)