h, w, n = map(int, input().split())
sr, sc = map(int, input().split())
S = input()[::-1]
T = input()[::-1]

r_bound = w
l_bound = 1
d_bound = h
u_bound = 1

remain = True

if S[0] =='R':
    r_bound -= 1
if S[0] =='L':
    l_bound += 1
if S[0] =='D':
    d_bound -= 1
if S[0] =='U':
    u_bound += 1

for s, t in zip(S[1:], T[1:]):
    if s =='R' and t !='L':
        r_bound -= 1
    if s =='L' and t !='R':
        l_bound += 1
    if s =='D' and t !='U':
        d_bound -= 1
    if s =='U' and t !='D':
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
