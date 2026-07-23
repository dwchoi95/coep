n = input()
for i in range(int(n)):
    xa, ya, ra, xb, rb, yb = list(map(float, input().split(" ")))
    d = abs(complex(xb-xa, yb-ya))
    if ra + rb < d:
        print("0")
    elif abs(rb-ra) <= d <= ra+rb:
        print("1")
    elif d < abs(ra-rb):
        print("2" if ra > rb else "-2")