N = int(input())
A = list(map(int, input().split()))
B = list(map(int, input().split()))

cnt = 0
for n in range(N):
    if A[n] <= B[n]:
        cnt += A[n]
        B[n] -= A[n]
        if A[n+1] < B[n]:
            cnt += A[n+1]
            A[n+1] = 0
        else:
            cnt += B[n]
            A[n+1] -= B[n]
    else:
        cnt += B[n]
        
print(cnt)