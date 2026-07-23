n, m = input().split()
b = input().split()
sum = 0
for x in b:
    sum += int(x)
yy=0
for y in b:
    if int(y) >= sum/(4*int(m)):
        yy+=1
if yy < int(m):
    print("No")
else:
    print("Yes")