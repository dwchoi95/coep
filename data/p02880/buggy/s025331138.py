N = int(input())
for i in range(9):
  for j in range(9):
    if i * j == N:
      print('Yes')
      exit()
print('No')