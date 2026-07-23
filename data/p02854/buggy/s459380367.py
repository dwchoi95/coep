n,*a=map(int,open(0).read().split())
b=sum(a)
c=b
d=200000
for i in a:
    c-=i
    if c<0:
        break
    d=min(d,c)
print(d)