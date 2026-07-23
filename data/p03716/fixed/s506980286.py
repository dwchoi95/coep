import heapq
N = int(input())
a = list(map(int, input().split()))

max_result = -1000000

big_a = a[:N]
big_sum = [sum(big_a)]
heapq.heapify(big_a)
for i in range(N):
  heapq.heappush(big_a, a[N+i])
  p = heapq.heappop(big_a)
  big_sum.append(big_sum[-1] + a[N+i] - p)

small_a = [-i for i in a[-N:]]
small_sum = [sum(small_a)]
heapq.heapify(small_a)
for i in range(N):
  heapq.heappush(small_a, -a[-N-i-1])
  p = heapq.heappop(small_a)
  small_sum.append(small_sum[-1] - a[-N-i-1] - p)

max_result = -float('inf')

for m,s in zip(big_sum, small_sum[::-1]):
  max_result = max(m + s, max_result)

print(max_result)

