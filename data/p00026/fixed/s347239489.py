t = [[0 for i in range(10)] for j in range(10)]
case1 = [(0, 0), (0, -1), (1, 0), (0, 1), (-1, 0)]
case2 = [(1, -1), (1, 1), (-1, 1), (-1, -1)]
case3 = [(0, -2), (2, 0), (0, 2), (-2, 0)]
while True:
    try:
        x, y, s = map(int, input().split(','))
    except:
        break
    for c in [case1, case2, case3][:s]:
        for _x, _y in c:
            if y+_y < 0 or x+_x < 0:
                continue
            try:
                t[y+_y][x+_x] += 1
            except IndexError:
                continue

print(sum(1 for l in t for v in l if not v))
print(max(v for l in t for v in l))