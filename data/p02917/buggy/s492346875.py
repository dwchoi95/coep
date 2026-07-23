N=int(input())
B=[10**6]
B.extend([int(b) for b in input().split()])
B.append(10**6)
print(N, B)

A=[None]*N
for i in range(N):
  A[i] = min(B[i], B[i+1])
  
print(sum(A))