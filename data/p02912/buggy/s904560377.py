import sys
import heapq
input=sys.stdin.readline
n,m=map(int,input().split())
a=list(map(lambda x:int(x)*(-1),input().split()))
heapq.heapify(a)
for _ in range(m):
    heapq.heappush(a,heapq.heappop(a)/2)
print(int(sum(a)*(-1)))