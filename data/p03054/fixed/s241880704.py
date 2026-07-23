H, W, N = map(int, input().split())
Sr, Sc = map(int, input().split())
S = input()
T = input()


l = 1
r = W
u = 1
d = H

for s, t in zip(S[::-1], T[::-1]):

    if t=="L":
        r = min(r+1, W)
    elif t=="R":
        l = max(l-1, 1)
    elif t=="U":
        d = min(d+1, H)
    else:
        u = max(u-1, 1)

    
    if s=="L":
        l+=1
    elif s=="R":
        r-=1
    elif s=="U":
        u+=1
    else:
        d-=1

    if l > r or u > d:
        print("NO")
        exit()
    
if u<=Sr<=d and l<=Sc<=r:
    print("YES")
else:
    print("NO")
