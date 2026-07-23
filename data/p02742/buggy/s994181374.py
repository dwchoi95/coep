H,W=map(int,input().split())
if H%2==1 and W%2==1:
    print((H*W+1)/2)
else:
    print(H*W/2)