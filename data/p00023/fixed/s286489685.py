n = int(input())
for i in range(n):
    k = input()
    xa, ya, ra, xb, yb, rb = list(map(float, k.split(" ")))
    d = abs(complex(xb-xa, yb-ya))
    if ra + rb < d:
        print("0")
    elif abs(rb-ra) <= d <= ra+rb:
        print("1")
    else:
        print("2" if ra > rb else "-2")