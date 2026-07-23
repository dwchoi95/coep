N = int(input())
B = list(map(int, input().split()))

A = [max(B)] * N

for n in range(N, 0, -1):
    if A[n-1] > B[n-2]:
        A[n-1] = B[n-2]
    if A[n-2] > B[n-2]:
        A[n-2] = B[n-2]
print(sum(A))