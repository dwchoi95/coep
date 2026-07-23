import math
a=int(input())
if a%2==0:
  print(int(a*a/4))
else:
  print(math.ceil(a/2)*math.floor(a/2))