n,c=map(int,input().split())
l=[list(map(int,input().split())) for i in range(n)]

rev=[None]*(n+1)
norm=[None]*(n+1)
rev[0]=(0,0)
norm[0]=(0,0)
ans=0


for i in range(1,n+1):
    x,v=l[i-1]
    norm[i]=(x,v+norm[i-1][1])


for i in range(1,n+1)[::-1]:
    x,v=l[i-1]
    if i==n:
        rev[i]=(c-x,v)
    else:
        rev[i]=(c-x,v+rev[i+1][1])

for i in range(n+1):
    for j in range(n-i):
        cost=min(norm[i][0]+2*rev[-j][0],2*norm[i][0]+rev[-j][0])
        ans=max(ans,rev[-j][1]+norm[i][1]-cost)

print(ans)