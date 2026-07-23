N, M = map(int, input().split())
mvals = list(map(lambda x: -int(x), input().split()))

import heapq
heapq.heapify(mvals)

for _ in range(M):
    price = heapq.heappop(mvals)
    heapq.heappush(mvals, price / 2)

res = -int(sum(mvals))
print(res)