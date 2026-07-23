H,W=map(int,input().split())
import math

A=[0,math.ceil(W/2)]
if (H-1)*(W-1)!=0:
  c=W*math.floor(H/2)+A[H%2]
else:
  c=1
print(c)