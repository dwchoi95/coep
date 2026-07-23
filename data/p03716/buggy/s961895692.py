import heapq
n=int(input())
a=list(map(int,input().split()))
q=a[0:n]
heapq.heapify(q)
p=list(map(lambda x: x*(-1),a[2*n:3*n]))
heapq.heapify(p)
sums=[0]*(n+1)
sums[0]=sum(q)
sums[n]=sum(p)
am=a[n:2*n]
for i in range(0,n):
    heapq.heappush(q,am[i])
    heapq.heappop(q)
    sums[i+1]=sum(q)
for i in range(n-1,-1,-1):
    heapq.heappush(p,(-1)*am[i])
    heapq.heappop(p)
    sums[i]+=sum(p)
print(max(sums))