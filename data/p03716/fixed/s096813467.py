

from heapq import heappush, heappop
import sys

N = int(input())
a = list(map(int,input().split()))

hq = []
hq_r = []
for i in range(N):
    heappush(hq,a[i])
    heappush(hq_r,-1*a[-1-i])


max_A = [0 for _ in range(N+1)]
max_A[0] = sum(hq)

min_C = [0 for _ in range(N+1)]
min_C[0] = sum(hq_r) * (-1)

for i in range(N):
    heappush(hq, a[N+i])
    heappush(hq_r, -1*a[-N-1-i])
    minus = heappop(hq)
    minus_r = heappop(hq_r)
    max_A[i+1] = max_A[i] + a[N+i] - minus
    min_C[i+1] = min_C[i] + a[-N-1-i] + minus_r
    
max_val = -10e+100
for i in range(N+1):
    kari = max_A[i] - min_C[-1-i]
    if max_val < kari:
        max_val =kari
print(max_val)