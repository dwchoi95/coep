
import sys, math, heapq,copy
input = lambda: sys.stdin.buffer.readline().rstrip().decode('utf-8')
sys.setrecursionlimit(10**8)
inf = float('inf')
ans=count=0


ans = -inf
n = int(input())
A = list(map(int, input().split()))
AL, AR = A[:n], A[2*n:]
al,ar=copy.copy(AL),copy.copy(AR)
AN = A[n:2*n]
LS, RS = sum(AL), sum(AR)
AR = list(map(lambda ddd: -ddd, AR))
heapq.heapify(AL)
heapq.heapify(AR)
tmp=LS
ANSR=[0]*n
ANSL=[0]*n

for i in range(n):
    if AN[i]-AL[0] >0:
        LS = LS-heapq.heappop(AL)+AN[i]
        heapq.heappush(AL,AN[i])
    ANSL[i] = LS

LS=tmp
for j in range(n-1,-1,-1):
    if 0 < -AR[0]-AN[j]:
        RS = RS+heapq.heappop(AR)+AN[j]
        heapq.heappush(AR,-AN[j])
    ANSR[j] = RS
ANSR=ANSR+[sum(ar)]
ANSL=[sum(al)]+ANSL
for i in range(n+1):
    ans=max(ans,ANSL[i]-ANSR[i])
print(ans)
