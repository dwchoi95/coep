import heapq

n,m = map(int,input().split())
price = [-int(i) for i in input().split()]

heapq.heapify(price)
for i in range(m):
    a = heapq.heappop(price)
    heapq.heappush(price,a)
print(-sum(price))
    