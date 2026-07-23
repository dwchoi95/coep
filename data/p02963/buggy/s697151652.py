n=int(input())
m=1000000000
l=[0,0]
if(n<=m):
    l.append(1)
    l.append(0)
    l.append(0)
    l.append(n)
else:
    l.append(1)
    l.append(m)
    x=n%m
    y=n
    l.append(m-x)
    l.append(y)
for i in l:
    print(i,end=" ")

