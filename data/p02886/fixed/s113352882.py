N = int(input())
d = [int(i) for i in input().split()]
sum = 0

for i in range(N):
  for j in range(N):
    if i != j:
      sum += d[i] * d[j]

print(int(sum/2))
