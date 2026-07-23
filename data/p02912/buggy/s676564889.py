import heapq, math
n, m = map(int, input().split())
a = list(map(int, input().split()))
ar = [-i for i in a]
heapq.heapify(ar)

while m > 0:
    discount = heapq.heappop(ar)
    heapq.heappush(ar, discount/2)
    m -= 1

print(math.floor(-sum(ar)))
