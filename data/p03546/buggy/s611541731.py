h,w=map(int,input().split())
wlist=[[0]*10 for _  in range(10)]
for i in range(10):
    b=list(map(int,input().split()))
    for j in range(10):
        wlist[i][j]=b[j]
for i in range(10):
    for j in range(10):
        for k in range(10):
            wlist[i][j]=min(wlist[i][j],wlist[i][k]+wlist[k][j])
ans=0
for _ in range(h):
    t=list(map(int,input().split()))
    for i in t:
        if i==-1 or i==1:
            continue
        else:
            ans+=wlist[i][1]
print(ans)