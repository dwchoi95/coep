a,b = map(int,input().split())
li = [-int(x) for x in input().split()]
import heapq
heapq.heapify(li)
for i in range(b):
    c = heapq.heappop(li)
    heapq.heappush(li,c/2)
li = [int(x) for x in li]
print(-sum(li))