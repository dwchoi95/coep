
import sys
import math
import heapq


def input(): return sys.stdin.buffer.readline().rstrip().decode('utf-8')


sys.setrecursionlimit(10**8)
inf = float('inf')
count = 0
ans = -inf
n = int(input())
A = list(map(int, input().split()))
AL = A[:n]
AR = A[2*n:]
AL.sort()
AR.sort(reverse=1)
i1 = i2 = j1 = j2 = 0
i = j = 0
ANL = A[n:2*n]
ANR = ANL[::-1]
LS = sum(AL)
RS = sum(AR)
heapq.heapify(AL)
AR = list(map(lambda ddd: -ddd, AR))

heapq.heapify(AR)
ans = max(ans, LS-RS)

for count in range(n):
    print(AL,AR)
    
    if ANL[i]-AL[0] > -AR[0]-ANR[j]:
        LS = LS-heapq.heappop(AL)+ANL[i]
        heapq.heappush(AL,ANL[i])
        i += 1
    else:
        RS = RS+heapq.heappop(AR)+ANR[j]
        heapq.heappush(AR,-ANR[j])
        j += 1
    
    ans = max(ans, LS-RS)
print(AL,AR)



print(ans)
