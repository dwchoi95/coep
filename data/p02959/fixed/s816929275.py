n=int(input())
a=[int(i) for i in input().split()]
b=[int(i) for i in input().split()]
asum=sum(a)
a1=a
ans=0
for i in range(n):
  if b[i]>=a1[i]+a1[i+1]:
    a1[i],a1[i+1]=0,0
    ans+=a1[i]+a1[i+1]
  elif b[i]>=a1[i]:
    a1[i+1]-=b[i]-a1[i]
    a1[i]=0
    ans+=b[i]
  else:
    a1[i]-=b[i]
    ans+=b[i]
print(asum-sum(a1))
