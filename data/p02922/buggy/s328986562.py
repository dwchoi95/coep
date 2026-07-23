a,b = map(int,input().split())
c = b 
if ((b > 1) and (b < a)) or (a==b):
    print(1)
elif b == 1:
    print(0)
else:
    print(c + 1)