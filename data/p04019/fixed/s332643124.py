k = str(input())


n = 0
w = 0
s = 0
e = 0
for i in range(len(k)):
    if k[i] == "N":
        n += 1
    elif k[i] == "W":
        w += 1
    elif k[i] == "S":
        s += 1
    else:
        e += 1
if (n == 0 and s > 0) or (s == 0 and n > 0) or (e == 0 and w > 0) or (w == 0 and e > 0):
    print("No")
else:
    print("Yes")