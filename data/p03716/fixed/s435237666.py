
def inpl(): return list(map(int, input().split()))
from heapq import heapify, heappop, heappush
from copy import deepcopy

N = int(input())
A = inpl()

before = deepcopy(A[:N])
heapify(before)
middle = A[N:-N]
after = [-a for a in A[-N:]]
heapify(after)

sb = sum(A[:N])
sa = -sum(A[-N:])

SB = [sb]
SA = [sa]

for m in middle:
    b = heappop(before)
    if b < m:
        heappush(before, m)
        sb += m - b
    else:
        heappush(before, b)
    SB.append(sb)    

for m in middle[::-1]:
    m = -m
    a = heappop(after)
    if a < m:
        heappush(after, m)
        sa += m - a
    else:
        heappush(after, a)
    SA.append(sa) 

    
print(max([b+a for b, a in zip(SB, SA[::-1])]))