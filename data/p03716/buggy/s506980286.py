import heapq
N = int(input())
a = list(map(int, input().split()))

max_result = -1000000

for k in range(N, 2*N+1):
  print("----------------")
  big_a = a[:k]
  heapq.heapify(big_a)
  print(big_a)
  small_a =[(-x, x) for x in a[k:]]
  heapq.heapify(small_a)
  print(small_a)

  for i in range(len(big_a) - N):
    heapq.heappop(big_a)
  print(big_a)

  for i in range(len(small_a) - N):
    heapq.heappop(small_a)
  print(small_a)

  big_sum = sum(big_a)
  small_sum = 0
  for i in small_a:
    small_sum += i[1]

  if (big_sum - small_sum) > max_result:
    max_result = big_sum - small_sum

print(max_result)

