x, y = map(int, input().split())

tmp = 4 * x - y
f = 0
if tmp % 2 == 0 and tmp >= 0:
    crane = tmp / 2
    turtle = x - crane
    if turtle >= 0:
        f = 1
    else:
        pass
else:
    pass

if f == 1:
    print('Yes')
else: 
    print('No')