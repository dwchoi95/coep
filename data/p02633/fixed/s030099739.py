X = int(input())

for k in range(1, 361):
    if (X * k) % 360 == 0:
        print(k)
        break