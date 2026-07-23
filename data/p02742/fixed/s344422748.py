import math
h,w = map(int,input().split())


if w == 1 or h == 1 :
    print("1")
elif (h * w ) % 2 == 0:
    result = h * w /2
    result = math.ceil(result)
    print(str(result))
elif (h * w )% 2 != 0:
    result = ((h * w) 
    result = math.ceil(result)
    print(str(result))
