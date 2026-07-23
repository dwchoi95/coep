a,b = map(int,input().split())
sum = 1
if ((b > 1) and (b < a)):
    print(1)
elif b == 1:
    print(0)
else:
    b = b - a
    while 0 < b:
        b = b - (a-1)
        sum=sum+1
    print(sum)