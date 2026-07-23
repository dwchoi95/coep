a, b = map(int, input().split())

if (b - a) % (a - 1) == 0:
  print(round((b - a) / (a - 1) + 1))
else:
  print(round((b - a) 