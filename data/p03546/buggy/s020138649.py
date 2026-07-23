h,w=map(int,input().split())
cost=[list(map(int,input().split())) for i in range(10)]
for i in range(10):
  for j in range(10):
    for k in range(10):
      cost[i][j]=min(cost[i][j],cost[i][k]+cost[k][j])
wall=[list(map(int,input().split())) for i in range(h)]
ans=0
for i in range(h):
  for j in wall[i]:
    if j==-1:continue
    ans+=cost[j][1]
print(ans)