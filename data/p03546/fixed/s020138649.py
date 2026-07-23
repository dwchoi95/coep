h,w=map(int,input().split())
cost=[list(map(int,input().split())) for i in range(10)]
for i in range(10):
  for j in range(10):
    for k in range(10):
      cost[j][k]=min(cost[j][k],cost[j][i]+cost[i][k])
ans=0
for i in range(h):
    a=map(int,input().split())
    for j in a:
        if j==-1:continue
        ans+=cost[j][1]
print(ans)