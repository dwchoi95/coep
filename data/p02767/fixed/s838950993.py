n = int(input())
x = [int(i) for i in input().split()]
l, r = x[0], x[0]
for i in x:
    l = min(l, i)
    r = max(r, i)
ans = 10e9
for i in range(l, r + 1):
    cost = 0
    for j in range(n):
        cost += (x[j] - i) ** 2
    ans = min(ans, cost)
print(ans)
