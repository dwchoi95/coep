
 
N = int(input())

B = [int(e) for e in input().split()]

A = [0] * N

A[0] = B[0]
A[1] = B[0]

for i in range(1, N - 1):
	A[i] = min(B[i], A[i])
	A[i + 1] = B[i]

print(sum(A))
