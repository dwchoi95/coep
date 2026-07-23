h,w = [int(i) for i in input().split()]
r = h*w
if r % 2 == 1:
    r += 1
if h <= 1 or w <= 1:
    print(1)
else:
    print(r 