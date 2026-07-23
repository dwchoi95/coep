n,m,c=map(int,input().split())
b=list(map(int,input().split()))
ans=0
for i in range(n):
    a=list(map(int,input().split()))
    d=0
    for j in range(m):
       d+=a[j]*b[j]
    d+=c
    if(d<=0):
        continue
    else:
     ans=i
print(ans)