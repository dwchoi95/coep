N = int(input())
A = list(map(int,input().split()))
S = []
P = A[:N]
Q = A[2*N:]
for i in range(N):
    Q[i] *= -1
R = A[N:2*N]
p = [0]*(N+1)
q = [0]*(N+1)
import heapq
heapq.heapify(P)
heapq.heapify(Q)
sp = sum(P)
sq = sum(Q)
p[0] = sp
q[0] = sq

for i in range(1,N+1):
    heapq.heappush(P,R[i-1])
    heapq.heappop(P)
    sp = sum(P)
    p[i] = sum(Q)
for i in range(1,N+1):
    heapq.heappush(Q,-R[-i])
    heapq.heappop(Q)
    sq = sum(Q)
    q[i] = sq

ans = -(10**100)
for k in range(N+1):
    ans = max(ans,p[k] + q[N-k])
    
print(ans)
