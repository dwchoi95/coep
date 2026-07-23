N = int(input())

P = [[int(_) for _ in input().split()] for n in range(N)]

X = []
Y = []
for x, y in P:
    X.append(x)
    Y.append(y)
mx = (min(X) + max(X)) 
my = (min(Y) + max(Y)) 

Qx = []
Qy = []
for x, y in P:
    x, y = x-mx, y-my
    Qx.append(x+y)
    Qy.append(x-y)

ax = max(Qx) - min(Qx)
ay = max(Qy) - min(Qy)
ans = max(ax, ay)
print(ans)
