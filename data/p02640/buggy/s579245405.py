X,Y = map(int, input().split())
if Y%2==1:
    print("NO")
else:
    kame=Y
    Y-=(kame*4)
    turu=Y
    if (turu+kame)==X:
        print("Yes")
    else:
        print('No')
