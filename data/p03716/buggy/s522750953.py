import heapq

N = int(input())
A = list(map(int,input().split()))
C = A[N:(2*N)]

L = []
R = []
for i in range(N):
  heapq.heappush(L,A[i]) 
  heapq.heappush(R,-A[-1-i]) 
  


lp = 0 
rp = 0
for i in range(N):
  
  if C[lp] - L[0] >= -C[-1-rp] - R[0]: 
    heapq.heappush(L, C[lp]) 
    temp = heapq.heappop(L)
    lp += 1
  else:
    heapq.heappush(R, -C[-1-rp])
    temp = heapq.heappop(R)    
    rp += 1
print(L,R,lp,rp)
ans = sum(L) + sum(R)
print(ans)
    