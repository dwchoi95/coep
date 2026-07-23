X,Y = map(int, input().split())
if Y%2==1:
    print('No')
else:
    if X*2<=Y and Y<=X*4:
        print('Yes')
    else:
        print('No')
