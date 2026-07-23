H,W=map(int,input().split())
import math

A=[0,math.ceil(W/2)]
c=W*math.ceil(H/2)+A[H%2]

print(c)
