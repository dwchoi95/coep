n=int(input())
m=1000000000
l=[0,0]
if(n<=m):
    l.append(1)
    l.append(0)
    l.append(0)
    l.append(n)
elif(n == 1000000000000000000):
    l.append(m)
    l.append(0)
    l.append(0)
    l.append(m)
else:
    l.append(m)
    l.append(1)
    x=n%m
    l.append(m-x)
    l.append(((n)
for i in l:
    print(i,end=" ")

