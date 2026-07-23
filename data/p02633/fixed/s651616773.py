import math

X= int(input())
g = math.gcd(360,X)

if 360 % g != 0:
  print(360)
else:
  print(int(360/g))