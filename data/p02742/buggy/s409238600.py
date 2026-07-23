
from math import ceil
H, W = map(int, input().split())
if H == 1 or W == 1:
    print(1)
    exit()
ans = 0
ans += ceil(W / 2) * ceil(H / 2)
ans += W 
print(ans)