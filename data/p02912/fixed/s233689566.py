import heapq
import math

n, m = map(int, input().split())
goods = list(map(lambda x: int(x) * -1, input().split()))
heapq.heapify(goods)
for i in range(m):
    the_most_expensive = heapq.heappop(goods)
    heapq.heappush(goods, math.ceil(the_most_expensive / 2))

print(sum(goods) * -1)
