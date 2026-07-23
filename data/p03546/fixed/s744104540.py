H,W=map(int,input().split())

A = [list(map(int, input().split())) for _ in range(10)]

for a in range(10):
    for b in range(10):
        for c in range(10):
            A[b][c]=min(A[b][c],A[b][a]+A[a][c])

ans=0
D=[]
for j in range(H):
    C=list(map(int,input().split()))
    D.append(C)
        
for k in range(H):
    for l in range(W):
        if D[k][l]!=(-1) and D[k][l]!=(1):
            ans+=A[D[k][l]][1]
print(ans)