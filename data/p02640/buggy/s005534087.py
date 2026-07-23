a,b = map(int,input().split())

turu = 2
kame = 4
flag =0

for x in range(a + 1):
    for y in range(a + 1):
        if kame * x + turu * y == b or x + y <= a:
            flag += 1

if flag == 0:
    print("No")
else:
    print("Yes")