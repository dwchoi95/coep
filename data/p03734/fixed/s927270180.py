N, W = list(map(int, input().split()))

values = [[] for i in range(4)]

w0, v0 = list(map(int, input().split()))
values[0].append(v0)

for i in range(N-1):
    w, v = list(map(int, input().split()))
    values[w-w0].append(v)

for i in range(4):
    values[i].sort(reverse=True)
    for j in range(len(values[i])-1):
        values[i][j+1] = values[i][j] + values[i][j+1]
    values[i].append(0)

res = 0

for i1 in range(len(values[0])+1):
    for i2 in range(len(values[1])+1):
        for i3 in range(len(values[2])+1):
            for i4 in range(len(values[3])+1):
                if(w0*i1 + (w0+1)*i2 + (w0+2)*i3 + (w0+3)*i4 <= W):
                    res = max(res, values[0][i1-1] + values[1][i2-1] + values[2][i3-1] + values[3][i4-1])

print(res)