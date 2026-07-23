h, w, n = map(int, input().split())
sr, sc = map(int, input().split())
S = input()[::-1]
T = input()[::-1]

r_bound = w
l_bound = 1
d_bound = h
u_bound = 1

remain = True

for s, t in zip(S, T):
    if t =='R' and l_bound > 1:
        l_bound -= 1
    elif t =='L' and r_bound < w:
        r_bound += 1
    elif t =='D' and u_bound > 1:
        u_bound -= 1
    elif t =='U' and d_bound < h:
        d_bound += 1
    if s =='R':
        r_bound -= 1
    elif s =='L':
        l_bound += 1
    elif s =='D':
        d_bound -= 1
    elif s =='U':
        u_bound += 1
    if (r_bound < l_bound) or (d_bound < u_bound):
        remain = False
        break
if (sc < l_bound or sc > r_bound) or (sr < u_bound or sr > d_bound):
    remain = False

if remain:
    print('YES')
else:
    print('NO')