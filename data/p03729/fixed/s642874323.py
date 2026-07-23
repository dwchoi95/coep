a,b,c = input().split()


if a[-1] == b[0]:
    if b[-1] == c[0]:
        print("YES")

    elif b[-1] != c[0]:
        print("NO")

elif a[-1] != b[0]:
    print("NO")
