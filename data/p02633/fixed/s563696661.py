x = int(input())
for i in range(1, 360+1):
    if (x*i)%360 == 0:
        print(i)
        exit()
        