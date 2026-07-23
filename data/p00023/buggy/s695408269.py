import math
for i in range(int(input())):
    xa, ya, ra, xb, yb, rb = list(map(float, input().split()))

    d1 = math.sqrt((xa - xb) ** 2 + (ya - yb) ** 2)
    d2 = math.fabs(ra + rb)

    if d1 <= d2:
        if d1 <= ra or d1 <= rb:
            print(2 if ra > rb else -2)
        else:
            print(1)
    else:
        print(0)