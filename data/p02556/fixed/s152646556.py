def f(x, y):
    return x-y, x+y


n = int(input())
p = [list(map(int, input().split())) for i in range(n)]

max_x = -2000000000
min_x = 2000000000
max_y = -2000000000
min_y = 2000000000
for xi, yi in p:
    f1, f2 = f(xi, yi)
    max_x = max(max_x, f1)
    min_x = min(min_x, f1)
    max_y = max(max_y, f2)
    min_y = min(min_y, f2)

print(max(max_x - min_x, max_y - min_y))