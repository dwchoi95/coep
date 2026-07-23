r, d, x = map(int, input().split())

for i in range(x):
  x = r * x - d
  if i >= 10:
    break  
  print(x)