x, y = map(int, input().split())
ret = 'No'
for i in range(x):
    rem = y - 2*i
    if rem%4 == 0:
        ret = 'Yes'
        break
print(ret)