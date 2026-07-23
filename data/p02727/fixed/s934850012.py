import sys
x, y, a, b, c = [int(x) for x in input().split()]
p = [int(x) for x in input().split()]
q = [int(x) for x in input().split()]
r = [int(x) for x in input().split()]
p.sort(key=lambda x: -x)
q.sort(key=lambda x: -x)
r.sort(key=lambda x: -x)
ri = 0
pi = x
qi = y
while ri < len(r) and (0 < pi or 0 < qi):
    if 0 < pi and p[pi - 1] < r[ri] and (qi <= 0 or p[pi - 1] <= q[qi - 1]):
        ri += 1
        pi -= 1
    elif 0 < qi and q[qi - 1] < r[ri] and (pi <= 0 or q[qi - 1] <= p[pi - 1]):
        ri += 1
        qi -= 1
    else:
        break
print(sum(p[:pi]) + sum(q[:qi]) + sum(r[:ri]))
