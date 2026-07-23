

N, M, C= map(int, input().split())
B=list(map(int, input().split()))
count=0
for i in range(N):
    A=[]
    total=0
    A=list(map(int, input().split()))
    for j in range(M):
        total=total+(A[j]*B[j])
    else:
        if total+C>0:
            count+=1

print(count)
