h,w=map(int,input().split())
wlist=[list(map(int,input().split()))for _ in range(10)]
for i in range(10):
    for j in range(10):
        for k in range(10):
            wlist[j][k]=min(wlist[j][k],wlist[j][i]+wlist[i][k])
ans=0
for _ in range(h):
    t=list(map(int,input().split()))
    for i in t:
        if i==-1 or i==1:
            continue
        else:
            ans+=wlist[i][1]
print(ans)