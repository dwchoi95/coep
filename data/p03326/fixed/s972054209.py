import sys

stdin = sys.stdin

ni = lambda: int(ns())
na = lambda: list(map(int, stdin.readline().split()))
ns = lambda: stdin.readline()

n, m = na()

zs = []
for i in range(n):
    zs.append(na())

ans = 0
if m == 0:
    print(0)
else:
    for u in (-1, 1):
        for v in (-1, 1):
            for w in (-1, 1):
                vs = []
                for z in zs:
                    vs.append(z[0]*u+z[1]*v+z[2]*w)
                vs.sort()
                ans = max(ans, sum(vs[-m:]))

    print(ans)