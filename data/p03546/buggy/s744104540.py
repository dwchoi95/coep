H,W=map(int,input().split())

A=[]
for i in range(10):
    B=list(map(int,input().split()))
    A.append(B)


for a in range(10):
    for b in range(10):
        for c in range(10):
            A[a][b]=min(A[a][b],A[a][c]+A[c][b])

ans=0
D=[]
for j in range(H):
    C=list(map(int,input().split()))
    D.append(C)
        
for k in range(H):
    for l in range(W):
        if D[k][l]!=(-1):
            ans+=A[D[k][l]][1]
print(ans)