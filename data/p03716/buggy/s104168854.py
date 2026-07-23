INF=10**30
from heapq import heapify,heappop,heappush
N=int(input())
a=list(map(int,input().split()))

right=list(map(lambda x:-x,a[2*N:]));heapify(right)
rmin=[INF]*(3*N);rmin[2*N]=sum(right)*-1

for i in reversed(range(N,2*N)):
    p=heappop(right)*-1
    b=min(p,a[i])
    d=0 if b==p else b-p
    heappush(right,b*-1)
    rmin[i]=rmin[i+1]-d

left=a[:N];heapify(left)
lmax=[-INF]*(3*N);lmax[N-1]=sum(left)
for i in range(N,2*N):
    p=heappop(left)
    b=max(p,a[i])
    d=0 if b==p else b-p
    heappush(left,b)
    lmax[i]=lmax[i-1]+d
res=-INF
for i in range(N,2*N+1):
    res=max(res,lmax[i-1]-rmin[i])
print(res)