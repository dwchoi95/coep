n, m = map(int, input().split())
a = list(map(int, input().split()))
print("Yes") if len([a[i] for i in range(n) if a[i] >= sum(a) / 4 / m]) >= m else print("No")