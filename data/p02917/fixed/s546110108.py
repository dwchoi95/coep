N = int(input())
B = list(map(int, input().split()))

A = [max(B)] * N

for n in range(N-1):
    if B[n] < A[n]:
        A[n] = B[n]
    if B[n] < A[n+1]:
        A[n+1] = B[n]
print(sum(A))