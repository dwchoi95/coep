h,w = map(int,input().split())
ij = [list(map(int,input().split())) for x in range(10)]
for k in range(10):
    for i in range(10):
        for j in range(10):
            ij[i][j] = min(ij[i][j],ij[i][k]+ij[k][j])
ans = 0
for i in range(h):
    for j in list(map(int,input().split())):
        if j == -1:continue
        ans += ij[j][1]
print(ans)