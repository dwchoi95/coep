import sys
n1 = [[0, 1], [1, 0], [-1, 0], [0, -1]]
n2 = n1 + [[a, b] for a in [-1,1] for b in [-1, 1]]
n3 = n2 + [[a*2, b*2] for a, b in n1]
mas = [[0]*10 for i in range(10)]
for i in sys.stdin:
    try:
        x, y, a = list(map(int,i.split(",")))
        mas[y][x] += 1
        for j in eval("n"+str(a)):
            try:
                mas[y+j[1]][x+j[0]] += 1
            except IndexError:
                continue
    except:
        break
print(len([i for x in mas for i in x if not i]))
print(max([max(v) for v in mas]))