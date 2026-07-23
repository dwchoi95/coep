n = int(input())
x = list(map(int, input().split()))

p0 = sum(x)

cost = 10**9
for i in range(1,101):
    now = 0
    for j in x:
        now += abs(i-j)**2
    if cost > now:
        cost = now

print(now)
