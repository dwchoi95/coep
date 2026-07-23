from collections import deque
X,Y,A,B,C = (int(x) for x in input().split())
p = [[int(x), 'r'] for x in input().split()]
q = [[int(x), 'g'] for x in input().split()]
r = [[int(x), 'c'] for x in input().split()]
pqr = p + q + r
pqr.sort(reverse=True)
d = deque(pqr)
rem = X + Y
picked = 0
ans = 0
while rem > picked:
    pop = d.popleft()
    if pop[1] == 'r':
        if X > 0:
            X -= 1
            ans += pop[0]
            picked += 1
    elif pop[1] == 'g':
        if Y > 0:
            Y -= 1
            ans += pop[0]
            picked += 1
    else:
        rem -= 1
        ans += pop[0]
        picked += 1
print(ans)