H, W = map(int, input().split())
c = [[0]*10 for i in range(10)]
for i in range(10):
    a = list(map(int, input().split()))
    for j in range(10):
        c[i][j] = a[j]

A = [[0]*W for i in range(H)]
for i in range(H):
    a = list(map(int, input().split()))
    for j in range(W):
        A[i][j] = a[j]

for i in range(10):
    for j in range(10):
        for k in range(10):
            if i != j:
                c[i][j] = min(c[i][j], c[i][k]+c[k][j])

ans = 0
for i in range(H):
    for j in range(W):
        if A[i][j] != -1 and A[i][j] != 1:
            ans += c[A[i][j]][1]
print(ans)