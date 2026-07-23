a, b = map(int, input().split())
if b == 1:
    print(0)
    exit(0)
num = a
c = 1
while True:
    if num >= b:
        break
    else:
        num += a-1
        c += 1
print(c)