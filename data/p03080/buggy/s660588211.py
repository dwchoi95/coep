n=int(input())
s = input().split()

r = 0
b = 0
for i in s:
    if i == "R":
        r += 1
    if i == "B":
        b += 1

if r <= b:
    print("No")
else:
    print("Yes")