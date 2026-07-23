import sys
import math

n = int(input())

for _ in range(n):
    xa, ya, ra, xb, yb, rb = map(float, input().split())

    distance = math.sqrt(abs(xa-xb)**2 + abs(ya-yb)**2)
    if distance < ra + rb:
        if (ra < rb and distance < ra) or (ra > rb and distance < rb):
            print("2")
        else:
            print("1")
    else:
        print("0")