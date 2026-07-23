
from collections import defaultdict

H,W,M=map(int,input().split())
AB=[tuple(map(int,input().split()))for i in range(M)]
AB=[(a-1,b-1)for a,b in AB]
st=set(AB)

Wc=defaultdict(lambda :0)
Hc=defaultdict(lambda :0)
for a,b in AB:
    Hc[a]+=1
    Wc[b]+=1

Hm=max(Hc.values())
hhh=list(Hc.keys())
www=list(Wc.keys())
for i in hhh:
    if Hc[i]!=Hm:
        Hc.pop(i)
Wm=max(Wc.values())
for j in www:
    if Wc[j]!=Wm:
        Wc.pop(j)

ans=0
count=0
for i in Hc.keys():
    for j in Wc.keys():
        add = -1 if (i,j) in st else 0
        tmp= Hc[i] + Wc[j] + add
        ans=max(ans,tmp)
        if count>300000:
            break
        count+=1

print(ans)
