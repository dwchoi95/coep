import sys
input = sys.stdin.readline

N, M = map(int, input().split())
xyz = [None] * N
for i in range(N):
    _x, _y, _z = map(int, input().split())
    xyz[i] = [_x, _y, _z]
ans = 0
for i in range(2):
    for j in range(2):
        for k in range(2):
            sx, sy, sz = (-1)**i, (-1)**j, (-1)**k
            xyz.sort(key = lambda v : -(sx * v[0] + sy * v[1] + sz * v[2]))
            X, Y, Z = 0, 0, 0
            for i in range(M):
                X += xyz[i][0]
                Y += xyz[i][1]
                Z += xyz[i][2]
            ans = max(ans, abs(X) + abs(Y) + abs(Z))
print(ans)