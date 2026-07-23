N, K = map(int, input().split())
X = list(map(int, input().split()))
INF = 1000000000
distances = [INF]*(2*(N-K+1))
for l in range(N-K+1):
    distances[l]=abs(X[l]) + abs(X[l] - X[l+K-1])
    distances[l+1]=abs(X[l+K-1]) + abs(X[l] - X[l+K-1])

print(min(distances))
