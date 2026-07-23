x,y = list(map(int, input("").split()))

if 4 * x < y:
    print("No")
else:
    if y % 2 == 0:
        print("Yes")
    else:
        print("No")