N = int(input())
arr = sorted(list(map(int,input().split())))
b = {}
for i in arr:
    if i not in b:
        b[i] = 1
    else:
        b[i] += 1
h = 0
w = 0
for i in b:
    if b[i] >= 4 and h*w < i**2:
        h = i
        w = i
    elif b[i] >= 2:
        if w*i > h*i:
            h = i
        else:
            w = i
print(0)
