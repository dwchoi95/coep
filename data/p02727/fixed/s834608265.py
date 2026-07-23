from collections import deque
X,Y,A,B,C = (int(x) for x in input().split())
p = [[int(x), 'r'] for x in input().split()]
q = [[int(x), 'g'] for x in input().split()]
r = [[int(x), 'c'] for x in input().split()]
pqr = p + q + r
pqr.sort(reverse=True)
d = deque(pqr)
rem = X + Y
pickedr = 0
pickedg = 0
pickedc = 0
ans = 0
if len(d) <= rem:
    print(sum([apple[0] for apple in pqr]))
else:
    while pickedr + pickedg + pickedc < rem:
        pop = d.popleft()
        if pop[1] == 'r':
            if pickedr < X:
                ans += pop[0]
                pickedr += 1
        elif pop[1] == 'g':
            if pickedg < Y:
                ans += pop[0]
                pickedg += 1
        else:
            ans += pop[0]
            pickedc += 1
    print(ans)