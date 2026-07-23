a, b = map(int, input().split())
num = a
for i in range(50):
    if num > b:
        break
    else:
        num -= 1
        num += a
print(i+1)