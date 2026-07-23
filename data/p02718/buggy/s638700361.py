a,a1 = input().split()
b = input().split()
sum = 0
for _ in b:
    sum += int(_)
if int(b[int(a1) - 1]) < sum/4:
    print("Yes")
else:
    print("No")
