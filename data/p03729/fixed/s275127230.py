a,b,c = input().split()

if a[-1] == b[0]:
    if b[-1] == c[0]:
        print("YES")
    else:
        print("NO")
else:
    print("NO")