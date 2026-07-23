n = int(input())
x = [int(i) for i in input().split()]
l, r = 0, 0
for i in x:
    l = min(l, i)
    r = max(l, i)
ans = 10e9
for i in range(l, r):
    cost = 0
    for j in range(n):
        cost += (x[j] - i) * (x[j] - i)
    ans = min(ans, cost)
print(ans)
