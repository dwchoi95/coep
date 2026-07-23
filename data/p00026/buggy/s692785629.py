

paper = [0 for i in range(100)]
white_points = None
deep_points = None

def small(x, y):
    p = [[x, y]]
    for i, j in zip([-1, 0, 1, 0], [0, -1, 0, 1]):
        p.append([x + i, y + j])
    return p

def middle(x, y):
    p = small(x, y)
    for i, j in zip([1, -1] * 2, [1, 1, -1, -1]):
        p.append([x + i, y + j])
    return p

def big(x, y):
    p = middle(x, y)
    for i, j in zip([-2, 0, 2, 0], [0, -2, 0, 2]):
        p.append([x + i, y + j])
    return p

while True:
    try:
        x, y, size = map(int, input().split(','))
    except:
        print(paper.count(0))
        print(max(paper))
        break

    if size == 1:
        bp = small(x, y)
    elif size == 2:
        bp = middle(x, y)
    elif size == 3:
        bp = big(x, y)
    for p in bp:
        if not 0 <= p[0] * 10 + p[1] <= 99: continue
        paper[p[0] * 10 + p[1]] += 1