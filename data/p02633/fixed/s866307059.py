a = int(input())
for i in range(1,361):
    if i * a % 360 == 0:
        print(int(i))
        break
