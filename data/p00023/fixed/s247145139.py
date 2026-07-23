

import math 

num = int(input())
for i in range(num):
    ax,ay,ar,bx,by,br=map(float,input().split())
    d = ((ax-bx)* (ax - bx))+((ay-by)*(ay-by))
    r1 = (ar+br)*(ar+br)
    r2 = (ar-br)*(ar-br)
    if d <= r1 and d >= r2:
        print(1);
    elif d<r2 and ar>=br:
        print(2)
    elif d < r2 and ar <= br:
        print(-2)
    else:
        print(0)
    