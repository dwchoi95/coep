x, y = map(int, input().split())
ret = 'No'
for i in range(x+1):
    rem = y - 2*i
    if 4*(x - i) == rem:
        ret = 'Yes'
        break
print(ret)