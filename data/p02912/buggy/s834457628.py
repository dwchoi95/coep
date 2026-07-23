N, M = map(int, input().split())

A_list = list(map(int, input().split()))

a = list(map(lambda x: x*(-1), A_list))

import heapq
import math


heapq.heapify(a)

print(a)


for i in range(M):
        max_p = heapq.heappop(a)
        max_p = max_p / 2
        heapq.heappush(a, max_p)

res=0
for i in range(N):
        a[i] = -a[i]
        res += math.floor(a[i])

print(res)