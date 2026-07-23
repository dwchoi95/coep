h,w,m=map(int,input().split())
bomb=[list(map(int,input().split())) for _ in range(m)] 
a=[0 for i in range(h+1)] 
b=[0 for _ in range(w+1)] 
for i in range(m):
    a[bomb[i][0]]+=1
    b[bomb[i][1]]+=1
am=max(a) 
bm=max(b) 
hmax=[0]*(h+1) 
wmax=[0]*(w+1) 
for i in range(h+1):
    if am==a[i]:
        hmax[i]+=1
for i in range(w):
    if bm==b[i]:
        wmax[i]+=1
ans=(am+bm) 
k=sum(hmax)*sum(wmax)
if k>m: 
    print(ans)
    exit()
for i in bomb:
    if hmax[i[0]]==1 and wmax[i[1]]==1:
        k-=1
if k==0:
    print(ans-1)
else:
    print(ans)