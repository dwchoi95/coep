n, k = [int(i) for i in input().split()]
aa = [int(i) for i in input().split()]

ans = float("inf")
for bit in range(1<<n):
    if bin(bit).count("1") < k:
        continue
    if not (bit>>(n-1) & 1):
        continue
    now = aa[0]
    cost = 0
    for i in range(1, n):
        if bit>>i & 1:
            if aa[i] > now:
                now = aa[i]
            else:
                now = now + 1
                cost += now - aa[i]
        else:
            if aa[i] > now:
                continue

    ans = min(ans, cost)

print(ans)
