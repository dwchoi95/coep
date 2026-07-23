N, M, C = input().split(' ')
N = int(N)
M = int(M)
C = int(C)
B = []
B = input().split(' ')
B = [int(i) for i in B]
A = []
R = 0
for i in range(N):
  A = input().split(' ')
  A = [int(i) for i in A]
  combine = [x * y for (x, y) in zip(A, B)]
  if sum(combine) + C > 0:
    R += 1
print(R)