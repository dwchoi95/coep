
 
N = int(input())

B = [int(e) for e in input().split()]

A = [0] * N
A[N - 1] = B[N - 2]
A[N - 2] = B[N -2]


for i in reversed(range(0, N - 1)):
	A[i] = min(A[i], B[i - 1])
	A[i - 1] = B[i - 1]


print(sum(A))
