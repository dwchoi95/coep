a = list(input())
b = list(input())
c = list(input())
check = "a"
while True:
    if check == "a":
        if len(a) == 0:
            print("A")
            break
        else:
            check = a[0]
            a.pop(0)
    if check == "b":
        if len(b) == 0:
            print("B")
            break
        else:
            check = b[0]
            b.pop(0)
    if check == "c":
        if len(c) == 0:
            print("C")
            break
        else:
            check = c[0]
            c.pop(0)