n = input(int())
d = list(map(int, input().split()))

ans = 0
for i in range(len(d)):
    for j in range(i+1, len(d)):
        ans += d[i] * d[j]

print(ans)
