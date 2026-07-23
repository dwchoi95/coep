import heapq
from collections import deque
N = int(input())
A = list(map(int, input().split()))

al = A[:N]
ar = [-a for a in A[2*N:]]
ac = deque(A[N:2*N])
heapq.heapify(al)
heapq.heapify(ar)
for i in range(N):
    gl = ac[0] - al[0]
    gr = -ar[0] - ac[-1]
    if gl < 0 and gr < 0:
        ac.pop()
    elif gl > gr:
        heapq.heappop(al)
        tmp = ac.popleft()
        heapq.heappush(al, tmp)
    else:
        heapq.heappop(ar)
        tmp = ac.pop()
        heapq.heappush(ar, -tmp)
print(sum(al)+sum(ar))
