X = int(input())

for k in range(1, 361):
    if ((180 - X) * k) % 360 == 0:
        print(k)
        break