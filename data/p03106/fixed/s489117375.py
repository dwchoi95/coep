a=[0,0]
s=[]
a[0],a[1],k=map(int,input().split())
for i in range(1,min(a)+1):
  if a[0]%i==0 and a[1]%i==0:
    s.append(i)
print(s[len(s)-k])