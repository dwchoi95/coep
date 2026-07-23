x = int(input())

for k in range(1, 10000):
    if x*k % 360 == 0:
        print(k)
        break
