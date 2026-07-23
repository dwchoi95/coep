import sys
from collections import Counter
input = sys.stdin.readline

X, Y, A, B, C = map(int, input().split())
p = list(map(int, input().split()))
q = list(map(int, input().split()))
r = list(map(int, input().split()))

p.sort()
q.sort()
r.sort()

if A > X:
    p = p[-X:]
if B > Y:
    q = q[-X:]

p.extend(q)
p.extend(r)

p.sort()

print(sum(p[-(X+Y):]))