N = int(input())
A = list(map(int,input().split()))
ans = 0
K = max(A)+1
for i in range(N-2):
    if A[i] == A[i+1]:
        A[i+1] = K
        K += 1
        ans += 1
print(ans)