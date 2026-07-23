import math
x=int(input())
ct=0
for i in range(1000):
  ct+=(180-x)
  if ct%360==0:
    print(i+1)
    exit()