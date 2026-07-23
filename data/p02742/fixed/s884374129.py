import math
H,W=map(int,input().split())
if H==1 or W==1:
    print(1)
elif (H*W)%2==0:
    print(H*W
else:
    print(math.ceil(H*W/2))