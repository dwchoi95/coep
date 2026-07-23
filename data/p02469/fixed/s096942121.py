def gcd(x,y):
    p=min(x,y)
    q=max(x,y)
    while p != q:
        if q > p:
            q = q - p
        else:
            p = p - q
    return q

c=0
n=int(input())
a=sorted(set(list(map(int, input().split()))))
b=[]
while len(a) > 1:
    p=a[0]
    q=a[1]
    g=gcd(p,q)
    if g !=0:
        a.append(p*q
    a.pop(0)
    a.pop(0)
    a=sorted(a)
print(*a)