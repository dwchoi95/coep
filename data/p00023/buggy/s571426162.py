

import math


num = int(input())

for i in range(num):
    ax,ay,ar,bx,by,br = map(float,input().split(' '))
    d = (ax - bx)**2 + (ay * by)**2
    if d < abs(br - ar):
        if ar > br:
            print(2)
        else:
            print(-2)
    elif d <= ar + br:
        print(1)
    else:
        print(0)