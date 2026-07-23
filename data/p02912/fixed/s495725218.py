import math
import heapq

N, M = list(map(int, input().split()))
A = list(map(lambda a: -int(a), input().split()))
A.sort()
heapq.heapify(A)

for i in range(M):
  a = heapq.heappop(A)
  a /= 2.0
  heapq.heappush(A, a)

amount = 0
for a in A:
  amount += math.floor(-a)
print(amount)