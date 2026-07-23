s = list(input())
N = 0
W = 0
S = 0
E = 0
for i in s:
  if i == 'N':
    N = 1
  if i == 'W':
    W = 1
  if i == 'S':
    S = 1
  if i == 'E':
    E = 1
if ((N == 0 and S == 0) or (N == 1 and S == 1)) and ((W == 0 and E == 0) or (W == 1 and E == 1)):
  print('Yes')
else:
  print('No')