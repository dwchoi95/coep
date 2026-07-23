def f(x, y):
    return x-y, x+y


n = int(input())
p = [list(map(int, input().split())) for i in range(n)]

max_x = 0
min_x = 2000000000
max_y = 0
min_y = 2000000000
for xi, yi in p:
    x_, y_ = f(xi, yi)
    max_x = max(max_x, x_)
    min_x = min(min_x, x_)
    max_y = max(max_y, y_)
    min_y = min(min_y, y_)

print(max(max_x - min_x, max_y - min_y))