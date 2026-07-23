from itertools import product as prod
avail_numbers = [(i + 1) * (j + 1) for i, j in prod(range(9), range(9))]

if int(input()) in avail_numbers:
  print("Yes")
else:
  print("No")
