H, W, N = map(int, input().split())
sr, sc = map(int, input().split())
S = input()
T = input()
l = 0
r = W+1
u = 0
d = H+1
for s,t in zip(S[::-1],T[::-1]):
    if s == 'L' and t != 'R':
        l += 1
    if s == 'R' and t != 'L':
        r -= 1
    if s == 'U' and t != 'D':
        u += 1
    if s == 'D' and t != 'U':
        d -= 1
    if l == r-1 or u == d-1:
        break
if l < sc < r and u < sr < d:
    print('YES')
else:
    print('NO')