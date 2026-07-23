import sys
input = sys.stdin.readline
from itertools import product
n, m = map(int, input().split())
xyz = [list(map(int, input().split())) for _ in range(n)]

ans = 0
for p in product([1, -1], repeat=3):
    temp = []
    for x, y, z in xyz:
        x*=p[0];y*=p[1];z*=p[2]
        temp.append(x+y+z)
    temp.sort(reverse=True)
    ans = max(ans, sum(temp[:m]))
print(ans)