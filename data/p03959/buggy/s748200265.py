n=int(input())
t=[int(j) for j in input().split()]
a=[int(j) for j in input().split()]
tmp=0
l=[]
for i in t:
    if tmp<i:
        l.append(-i)
        tmp=i
    else:
        l.append(i)
tmp=0
ans=1
mod=10**9+7
for i in range(n)[::-1]:
    if tmp<a[i]:
        if l[i]>=a[i]:
            tmp=a[i]
        else:
            if l[i]>0:
                print(0)
                exit()
    else:
        if l[i]>0:
            ans=(ans*min(a[i],l[i]))%mod
print(ans)