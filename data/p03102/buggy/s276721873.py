N,M,C=map(int, input().split())
B=list(map(int, input().split()))
A=[]
ans=0
a=0
for i in range(N):
    A.append([int(j) for j in input().split()])
for i in range(N):
    for j in range(M):
         a+=A[i][j]*B[j]
    if a+C==0:
        ans+=1
print(ans)