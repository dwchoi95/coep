S = input()
N = len(S)
A = []

for i, s in enumerate(S):
  if s == "W":
    A.append(i)

print(max(sum(A)-len(A), 0))