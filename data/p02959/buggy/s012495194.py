n=int(input())
a=list(map(int,input().split()))
b=list(map(int,input().split()))
c=0
for i in range(n):
  if a[i]>b[i]:
    c+=b[i]
  elif a[i]<=b[i]:
   
    if a[i+1]-(b[i]-a[i])>=0:
      c+=b[i]
      a[i+1]==a[i+1]-(b[i]-a[i])
    else:
      c+=a[i+1]
      a[i+1]==0
print(c)

