from sys import exit
H, W, N = map(int, input().split())
sr, sc = map(int, input().split())
S = input()
T = input()
ul = 1
dl = H
rl = W
ll = 1
for s, t in zip(S[1::][::-1], T[:-1:][::-1]):
    if s == 'U':
        ul += 1
    elif s == 'D':
        dl -= 1
    elif s == 'L':
        ll += 1
    else:
        rl -= 1
    if ul > dl or ll > rl or ul == H + 1 or dl == 0 or ll == W + 1 or rl == 0:
        print('NO')
        exit()
    if t == 'U':
        dl = min(H, dl+1)
    elif t == 'D':
        ul = max(1, ul-1)
    elif t == 'L':
        rl = min(W, rl+1)
    else:
        ll = max(1, ll-1)
s = S[0]
if s == 'U':
    ul += 1
elif s == 'D':
    dl -= 1
elif s == 'L':
    ll += 1
else:
    rl -= 1

if ul <= sr <= dl and ll <= sc <= rl:
    print('YES')
else:
    print('NO')