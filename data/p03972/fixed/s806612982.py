import os
import sys

if os.getenv("LOCAL"):
    sys.stdin = open("_in.txt", "r")

sys.setrecursionlimit(2147483647)
INF = float("inf")
IINF = 10 ** 18
MOD = 10 ** 9 + 7


W,H = list(map(int, sys.stdin.readline().split()))
P = [int(sys.stdin.readline()) for _ in range(W)]
Q = [int(sys.stdin.readline()) for _ in range(H)]

edges = []
for p in P:
    edges.append((p, 'P'))
for q in Q:
    edges.append((q, 'Q'))
edges.sort()

ans = 0
a = W + 1
b = H + 1
for e, pq in edges:
    if pq == 'P':
        ans += e * b
        a -= 1
    else:
        ans += e * a
        b -= 1
print(ans)
