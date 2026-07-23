
n = int(input())
x = list(map(int, input().split()))
cost = 10**9
for i in range(1,100):
    now = 0
    for j in x:
        now += (i-j)**2
    if cost > now:
        cost = now
print(cost)
