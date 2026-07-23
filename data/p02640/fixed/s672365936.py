x,y = list(map(int,input().split()))

if ((4 * x) - y) % 2 == 0 and y >= 2 * x and  y <= 4 * x:
  print('Yes')
else:
  print('No')