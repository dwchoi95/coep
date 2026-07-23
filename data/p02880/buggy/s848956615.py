n=int(input())

for i in range(2,10):
  for j in range(2,10):
    if i*j==n:
      print('Yes')
      exit()

print('No')
