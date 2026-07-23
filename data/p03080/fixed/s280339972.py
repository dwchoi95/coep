i = int(input())
hat = list(input())

B_count = hat.count('B')
R_count = hat.count('R')

if B_count < R_count:
  print("Yes")
else:
  print('No')