o = input()
e = input()
for i,a in enumerate(o):
    for j,b in enumerate(e):
        if(i == j):
            print(a + b, end = '')
    if i == len(o) - 1:
        print(a)
