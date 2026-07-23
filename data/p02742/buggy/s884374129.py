import math
H,W=map(int,input().split())
if (H*W)%2==0:
    print(int(H*W/2))
else:
    print(math.ceil(H*W/2))