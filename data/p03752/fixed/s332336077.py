N, K = map(int, input().split())
A = list(map(int, input().split()))

ans = float('inf')
for key in range(1 << N):
    if bin(key).count('1') < K:
        continue
    cost = 0
    height = 0
    for i in range(N):
        if not (key & (1 << i)):
            height = max(A[i], height)
            continue
        height = max(A[i], height+1)
        cost += height - A[i]
    ans = min(ans, cost)
print(ans)


