a, b = map(int, input().split())

if b - a == 1:
  print(2)
else:
  print(round((b-1)/(a-1)))