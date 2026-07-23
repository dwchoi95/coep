x,y = list(map(int, input("").split()))

if 4 * x < y:
    print("No")
else:
    if 2 * x <= y:
        if y % 2 == 0:
            print("Yes")
        else:
            print("No")
    else:
        print("No")