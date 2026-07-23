N = int(input())

P = [[int(_) for _ in input().split()] for n in range(N)]

X = []
Y = []
for x, y in P:
    X.append(x)
    Y.append(y)
mx = (min(X) + max(X)) 
my = (min(X) + max(X)) 

Q = []
for x, y in P:
    x, y = x-mx, y-my
    Q.append((x+y, x-y))

ans = 0
for x, y in Q:
    ans = max(ans, abs(x) + abs(y))
print(ans)
