a = list(input())
b = list(input())
c = list(input())
check = "a"
while len(a) != 0 and len(b) != 0 and len(c) != 0:
    if check == "a":
        check = a[0]
        a.pop(0)
    elif check == "b":
        check = b[0]
        b.pop(0)
    else:
        check = c[0]
        c.pop(0)

if len(a) == 1:
    print("A")
elif len(b) == 1:
    print("B")
else:
    print("C")