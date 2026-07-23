x = int(input())

for n in range(1, 10000):
    k, y = divmod(360*n, (180-x))
    if y == 0:
        print(k)
        break
