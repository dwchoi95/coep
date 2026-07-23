N = int(input())
a = list(map(int, input().split()))

import heapq
que1 = []
heapq.heapify(que1)
S = [0] * (2*N + 1)
for i in range(N):
    S[i + 1] = S[i] + a[i]
    
    heapq.heappush(que1, a[i])
que2 = []
heapq.heapify(que2)
T = [0] * (2*N + 1)
for i in range(N):
    T[i + 1] = T[i] + a[3*N - i - 1]
    
    heapq.heappush(que2, -a[3*N - i - 1])

for i in range(N, 2*N):
    mi = heapq.heappop(que1)
    
    if a[i] > mi:
        S[i + 1] = S[i] - mi + a[i]
        
        heapq.heappush(que1, a[i])
    else:
        S[i + 1] = S[i]
        heapq.heappush(que1, mi)
for i in range(N, 2*N):
    ma = heapq.heappop(que2) * -1
    
    if a[3*N - i - 1] < ma:
        T[i + 1] = T[i] - ma + a[3*N - i - 1]
        
        
        heapq.heappush(que2, -a[3*N - i - 1])
    else:
        T[i + 1] = T[i]
        heapq.heappush(que2, -ma)

res = -float('Inf')
for i in range(N, 2*N + 1):
    res = max(res, S[i] - T[3*N - i])
print(res)
