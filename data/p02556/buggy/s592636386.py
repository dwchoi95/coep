n = int(input())
plus_max = 0
plus_min = 10**10
minus_max = 0
minus_min = 10**10
for _ in range(n):
    x, y = map(int, input().split())
    plus_max = max(plus_max, x + y)
    plus_min = min(plus_min, x + y)
    minus_max = max(minus_max, x - y)
    minus_min = min(minus_min, x - y)
print(max(plus_max - plus_min, minus_max - minus_min))
