import sys
import math

n = int(input())

for _ in range(n):
    xa, ya, ra, xb, yb, rb = map(float, input().split())

    distance = math.sqrt((xa-xb)**2 + (ya-yb)**2)
    if ra + rb >= distance:
        if (distance + ra < rb):
            print(-2)
        elif (distance + rb < ra):
            print(2)
        else:
            print(1)
    else:
        print(0)