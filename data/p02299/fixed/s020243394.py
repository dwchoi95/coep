n = int(input())
g = []
for i in range(n):
    g.append([int(i) for i in input().split()])
q = int(input())
EPS = 0.001
def dot(a, b):
    return sum([i * j for i,j in zip(a, b)])
def sub(a, b):
    return [a[0] - b[0],a[1] - b[1]]
def cross(a, b):
    return  a[0] * b[1] - a[1] * b[0]
def contains(g, p):
    x = False
    for i in range(n):
        a = sub(g[i], p)
        b = sub(g[(i+1)%n], p)
        if abs(cross(a, b)) < EPS and dot(a, b) < EPS: 
            return 1
        if a[1] > b[1]:
            a,b=b,a
        if a[1] < EPS and EPS < b[1] and cross(a,b) > EPS:
            x = not x
    return 2 if x else 0
for i in range(q):
    x,y = map(int, input().split())
    print(contains(g, [x,y]))

