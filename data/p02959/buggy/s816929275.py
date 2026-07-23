n=int(input())
a=[int(i) for i in input().split()]
b=[int(i) for i in input().split()]
a1=a
for i in range(n):
  if b[i]>=a[i]+a[i+1]:
    a[i],a[i+1]=0,0
  elif b[i]>=a[i]:
    a[i+1]=b[i]-a[i]
    a[i]=0
  else:
    a[i]-=b[i]
print(sum(a1)-sum(a))
    