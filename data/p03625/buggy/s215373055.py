from collections import Counter
n=int(input())
a=list(map(int,input().split()))
p=Counter(a)
c=0
d=0
for a,b in p.items():
    if b>3:
        if c<a:
            c=a
        if d<a:
            d=a
    elif b>1:
        if c==0:
            c=a
        else:
            if d>c:
                c=a
            else:
                d=a
print(c*d)