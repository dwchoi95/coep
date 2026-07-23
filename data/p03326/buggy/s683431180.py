N, M = map(int, input().split())
xyz = [list(map(int, input().split())) for i in range(N)]
tmp = [[0]*N for i in range(8)]

for n, _ in enumerate(xyz):
    x,y,z = _
    tmp[0][n] = x+y+z
    tmp[1][n] = x+y-z
    tmp[2][n] = x-y+z
    tmp[3][n] = x-y-z
    tmp[4][n] = -x+y+z
    tmp[5][n] = -x+y-z
    tmp[6][n] = -x-y+z
    tmp[7][n] = -x-y-z

result = [0]*8
for i in range(8):
    print(sorted(tmp[i]))
    result[i] = sum(sorted(tmp[i])[-M:])

print(max(result))