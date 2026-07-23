N, K = [int(i)for i in input().split()]
A = [int(i) for i in input().split()]


ans = float("inf")
for b in range(2 ** N):
    cnt = 0
    cost = 0
    height = A[0]
    for i in range(N):
        if i == 0:
            continue
        if (b >> i) & 1:
            cnt += 1
            cost += height - A[i] + 1
            height += 1
    if cnt + 1 == K:
        ans = min(ans, cost)

print(ans)
