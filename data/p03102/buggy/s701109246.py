NMC = list(map(lambda x: int(x), input().split()))
N = NMC[0]
M = NMC[1]
C = NMC[2]

B = list(map(lambda x: int(x), input().split()))
A = [list(map(lambda x: int(x), input().split())) for i in range(N)]

print("B", B)
print("A", A)
print("N", N)
print("M", M)
print("C", C)

answer = 0

for i in range(len(A)):
  judge = 0
  for m in range(len(A[i])):
    judge += A[i][m] * B[m]

  print("judge", judge)
  if (judge + C > 0):
    answer += 1

print(answer)