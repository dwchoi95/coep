a = int(input())
b = 0
for i in range(1,361):
    i += 1
    ans = i * a
    if ans == 360:
        print(int(i))
