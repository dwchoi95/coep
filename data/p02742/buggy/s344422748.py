import math
h,w = map(int,(input().split()))
h = math.floor(h)
w = math.floor(w)
sum = h * w

if h == 1 and w ==1:
    print("1")
elif h % 2 == 0:
    result = math.floor(sum /2)
    print(result)
else:
    result = math.floor(sum /2 + 1)
    print(result)