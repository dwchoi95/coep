N,M = map(int, input().split())
import heapq
A = list(map(int, input().split()))
A = [(-x,x) for x in A]
heapq.heapify(A)
for _ in range(M):
    a = heapq.heappop(A)[1]
    heapq.heappush(A, (-int(a/2), int(a/2)))
B = [a[1] for a in A]
print(sum(B))