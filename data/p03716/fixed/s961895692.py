import heapq
n=int(input())
a=list(map(int,input().split()))
q=a[0:n]
sums=[0]*(n+1)
sums[0]=sum(q)
heapq.heapify(q)
am=a[n:2*n]
for i in range(0,n):
    heapq.heappush(q,am[i])
    sums[i+1]=sums[i]+am[i]-heapq.heappop(q)
p=a[2*n:3*n]
p=list(map(lambda x: x*(-1),p))
sump=sum(p)
sums[n]+=sump
heapq.heapify(p)
for i in range(n-1,-1,-1):
    heapq.heappush(p,(-1)*am[i])
    sump=sump-am[i]-heapq.heappop(p)
    sums[i]+=sump
print(max(sums))