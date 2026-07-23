N,M=[int(i) for i in input().split()]
A = [int(i) for i in input().split()]
for i in range(M):
  l=A.index(max(A))
  A[l]
print(sum(A))