def gcd(x,y):
    p=min(x,y)
    q=max(x,y)
    while True:
            m=q%p
            if m==0:

                break
            p=m
            q=p

    if p==q:
        g=1
    else:
        g=p
    return g

c=0
n=int(input())
a=sorted(set(list(map(int, input().split()))))
b=[]
while len(a) > 1:
    n=len(a)
    for i in range(n-1):
        p=a[i]
        q=a[i+1]
        g=gcd(p,q)

        r=a[i]*a[i+1]
        b.append(r)
    a=sorted(b)
    b=[]
print(*a)