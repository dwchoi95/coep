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
b1 = sorted(b)[::-1]
for i in b1:
    if b[i] >= 4:
        if h < i:
            h = i
            w = i
            break
        else:
            w = i
            break
    elif b[i] >= 2:
        if h == 0:
            h = i
        else:
            w = i
            break
        
print(h*w)
