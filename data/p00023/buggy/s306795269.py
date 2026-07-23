

import math


num = int(input())

for i in range(num):
    ax,ay,ar,bx,by,br = map(float,input().split(' '))
    d = (ax - bx)*(ax - bx) + (ay * by)
    if d < (ar - br):
            print(2)
    if d < (br - ar):
            print(-2)
    elif d <= (ar + br):
        print(1)
    else:
        print(0)