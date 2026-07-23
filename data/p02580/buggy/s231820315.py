
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
for i in Hc.keys():
    if Hc[i]==Hm:
        x=i
        break
Wm=max(Wc.values())
for j in Wc.keys():
    if Wc[j]==Wm:
        y=j
        break


ans=Hc[x] + Wc[y] +(-1 if (x,y) in st else 0)
print(ans)
