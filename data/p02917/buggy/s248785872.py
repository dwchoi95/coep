N = int(input())
B = [int(i) for i in input().split()]

    
A = [0] * N
for i in range(1, N - 1):
    A[i] = min(B[i - 1], B[i])

A[N - 1] = B[N - 2]
print(sum(A))