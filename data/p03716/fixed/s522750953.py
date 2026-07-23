import heapq

N = int(input())
A = list(map(int,input().split()))
C = A[N:(2*N)]

L = []
R = []
for i in range(N):
  heapq.heappush(L,A[i]) 
  heapq.heappush(R,-A[-1-i]) 


ansL = [sum(L)]
for i in range(N):
  heapq.heappush(L,C[i])
  rmv = heapq.heappop(L)
  temp = ansL[i] + C[i] - rmv 
  ansL.append(temp)
  

ansR = [sum(R)]
for i in range(N):
  heapq.heappush(R,-C[-1-i])
  rmv = heapq.heappop(R)
  temp = ansR[i] - C[-1-i] - rmv
  ansR.append(temp)
  

ans = -float('inf')
for i in range(N+1):
  temp = ansL[i]+ansR[-1-i]
  ans = max(ans,temp)

print(ans)