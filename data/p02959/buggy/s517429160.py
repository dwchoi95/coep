N = int(input())
A = list(map(int,input().split()))
B = list(map(int,input().split()))
ans = 0
for i in range(N):
    print(i)
    if A[i] > B[i]:
        ans += B[i]
        A[i] -= B[i]
        B[i] -= B[i]
    else:
        ans += A[i]
        B[i] -= A[i]
        A[i] -= A[i]
    if A[i+1] > B[i]:
        ans += B[i]
        A[i+1] -= B[i]
        B[i] -= B[i]
    else:
        ans += A[i+1]
        B[i] -= A[i+1]
        A[i+1] -= A[i+1]
print(ans)
