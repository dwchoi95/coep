import heapq
N,M=[int(i) for i in input().split()]
A=sorted([-int(i) for i in input().split()])
for i in range(M):heapq.heappush(A,-(-heapq.heappop(A)
print(-sum(A))