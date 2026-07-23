import heapq, math
n, m = map(int, input().split())
a = list(map(int, input().split()))
ar = [-i for i in a]
heapq.heapify(ar)

for _ in range(m):
    discount = heapq.heappop(ar)
    heapq.heappush(ar, discount/2)

ans = 0
for i in ar:
    ans += math.floor(-i)

print(ans)