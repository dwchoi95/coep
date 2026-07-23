def read_line(*types): return [f(a) for a, f in zip(input().split(), types)]

w, h = read_line(int, int)

c = []
for _ in range(10):
    c.append(read_line(int, int, int, int, int, int, int, int, int, int))

for k in range(10):
    for i in range(10):
        for j in range(10):
            if i != j:
                c[i][j] = min(c[i][j], c[i][k] + c[k][j])

cost = 0
for _ in range(w):
    for a in read_line(*([int] * h)):
        if a > 0:
            cost += c[a][1]

print(cost)
