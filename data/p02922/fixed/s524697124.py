a, b = (int(i) for i in input().split())
count = 0
if b == 1:
    print("0")
    exit()
while True:
    b -= a
    count += 1
    if b <= 0: break
    b += 1
print(count)