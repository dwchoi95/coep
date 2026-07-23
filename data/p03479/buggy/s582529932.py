a = input().split()
ans=1
b=0
c=[int(a[0])]
while(0==0):
    if c[b]*2<int(a[1])-1:
        c.append(c[b]*2)
        b+=1
    else:
        print(len(c))
        break