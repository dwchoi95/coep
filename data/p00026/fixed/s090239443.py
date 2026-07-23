paper = [[0] * 10 for i in range(10)]

while True:
    try:
        x,y,s = map(int,input().split(','))
    except:
        break
    if s == 1:
        for i in range(10):
            for j in range(10):
                if abs(x - i) + abs(y - j) <= 1:
                    paper [i] [j] += 1
    elif s == 2:
        for i in range(10):
            for j in range(10):
                if abs(x - i) <= 1 and abs(y - j) <= 1:
                    paper [i] [j] += 1
    else:
        for i in range(10):
            for j in range(10):
                if abs(x - i) + abs(y - j) <= 2:
                    paper [i] [j] += 1

ls = sum(paper,[])
print(ls.count(0))
print(max(ls))