import sys
input = sys.stdin.readline
from heapq import *

n, m = map(int, input().split())
a = list(map(int, input().split()))
a = list(map(lambda x: x-1, a))
lr = []
cnt = 0

for i in range(n-1):
    ai, aj = a[i], a[i+1]
    
    if ai<aj:
        lr.append((ai+1, aj))
        cnt += aj-ai
    else:
        lr.append((ai-m+1, aj))
        lr.append((ai+1, m-1))
        cnt += m+aj-ai
    
lr.sort(key=lambda t: t[0])

idx = 0
ans = cnt
decre = 0
pq = []

for i in range(m):
    while len(pq)>0 and pq[0][0]<i:
        r, l = heappop(pq)
        
        decre -= r-l+1
        
    while idx<len(lr) and i>=lr[idx][0]:
        decre += i-lr[idx][0]
        
        heappush(pq, (lr[idx][1], lr[idx][0]))
        idx += 1
    
    ans = min(ans, cnt-decre)
    decre += len(pq)

print(ans)