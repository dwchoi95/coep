import heapq
X = list(map(int, input().split()))
A = list(map(int, input().split()))
heapq.heapify(A)

for i in range(X[1]):
  x = heapq.heappop(A) * (-1)
  heapq.heappush(A, int(x/2) * (-1))

ans = 0
for i in range(X[0]):
  ans += A[i]

print(ans)