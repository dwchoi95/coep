import heapq
import math

n, m = map(int, input().split())
a = list(map(int, input().split()))
q = []
heapq.heapify(q)

for i in range(n):
    heapq.heappush(q, -a[i])

for _ in range(m):
    b = heapq.heappop(q) / 2
    heapq.heappush(q, b)

print(math.floor(sum(q) * -1))
