S = input()
N = len(S)
A = []

for i, s in enumerate(S):
  if s == "W":
    A.append(i)
n = len(A)-1
print(sum(A)-(n+1)*n