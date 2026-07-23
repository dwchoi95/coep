N = int(input())
A = list(map(int, input().split()))
B = list(map(int, input().split()))

count = 0
for i in range(N):
    if A[i] < B[i]:
        count += A[i]
        B[i] -= A[i]
    else:
        count += B[i]
        B[i] = 0
    if A[i+1] < B[i]:
        count += A[i+1]
        B[i] -= A[i+1]
        A[i+1] = 0
    else:
        count += B[i]
        A[i+1] -= B[i]
        B[i] = 0
        
print(count)
