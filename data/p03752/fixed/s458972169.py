import itertools

n, k = [int(i) for i in input().split()]
top, *a = [int(i) for i in input().split()]

ans = float("inf")
for pp in itertools.product((0, 1), repeat=n-1):
    now = top
    v = 1
    cost = 0
    for i, p in enumerate(pp):
        if p == 0:
            if a[i] > now:
                now = a[i]
                v += 1
            continue
        now = max(now+1, a[i])
        cost += max(now-a[i], 0)
        v += 1
    if v >= k:
        ans = min(ans, cost)
print(ans)