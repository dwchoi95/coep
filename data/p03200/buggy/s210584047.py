S = input()
N = len(S)
A = []

for i, s in enumerate(S):
  if s == "W":
    A.append(i)

if len(A) == 1:
  print(sum(A))
else:
  print(sum(A)-len(A))