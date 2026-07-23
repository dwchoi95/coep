area = [[0 for i in range(10)] for j in range(10)]

while True:
    try:
        x, y, s = map(int, input().split(','))
    except:
        break

    if s == 3:
        if (0 <= x+2 <= 9) and (0 <= y <= 9):
            area[x+2][y] += 1
        if (0 <= x <= 9) and (0 <= y+2 <= 9):
            area[x][y+2] += 1
        if (0 <= x-2 <= 9) and (0 <= y <= 9):
            area[x-2][y] += 1
        if (0 <= x <= 9) and (0 <= y-2 <= 9):
            area[x][y-2] += 1
    if s >= 2:
        if (0 <= x+1 <= 9) and (0 <= y+1 <= 9):
            area[x+1][y+1] += 1
        if (0 <= x+1 <= 9) and (0 <= y-1 <= 9):
            area[x+1][y-1] += 1
        if (0 <= x-1 <= 9) and (0 <= y+1 <= 9):
            area[x-1][y+1] += 1
        if (0 <= x-1 <= 9) and (0 <= y-1 <= 9):
            area[x-1][y-1] += 1
    if s >= 1:
        if (0 <= x+1 <= 9) and (0 <= y <= 9):
            area[x+1][y] += 1
        if (0 <= x <= 9) and (0 <= y+1 <= 9):
            area[x][y+1] += 1
        if (0 <= x-1 <= 9) and (0 <= y <= 9):
            area[x-1][y] += 1
        if (0 <= x <= 9) and (0 <= y-1 <= 9):
            area[x][y-1] += 1
        area[x][y] += 1
        print(area)

max = 0
cnt = 0

for i in range(10):
    for j in range(10):
        if area[i][j] == 0:
            cnt += 1
        if area[i][j] > max:
            max = area[i][j]
print(cnt)
print(max)