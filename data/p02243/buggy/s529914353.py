from heapq import*
n=int(input())
A=[[]for _ in[0]*n]
for _ in[0]*n:
 e=list(map(int,input().split()))
 for i in range(e[1]):k=2*-~i;A[e[0]]+=[(e[k],e[k+1])]
H=[[0,0]]
d=[0]+[1e6]*n
c=[1]*n
while H:
 f=heappop(H)
 print(f)
 u=f[1]
 c[u]=0
 if d[u]>=f[0]:
  for s in A[u]:
   v=s[0]
   if c[v]and d[v]>d[u]+s[1]:
    d[v]=d[u]+s[1]
    heappush(H,[d[v],v])
for i in range(n):print(i,d[i])
