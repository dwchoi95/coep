h,w=map(int,input().split())
result = h*w
if result%2==0:
    print(result/2)
else:
    print(int(result/2)+1)