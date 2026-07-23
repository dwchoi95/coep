N = int(input())

able = False
for i in range(1, 10):
    for j in range(1, 10):
        if N == i * j:
            able = True
            break
    if able == True:
        break

if able == True:
    print('YES')
else:
    print('No')