import os
import sys

if os.getenv("LOCAL"):
    sys.stdin = open("_in.txt", "r")

sys.setrecursionlimit(2147483647)
INF = float("inf")
IINF = 10 ** 18
MOD = 10 ** 9 + 7

H, W = list(map(int, sys.stdin.readline().split()))
P = [int(sys.stdin.readline()) for _ in range(W)]
Q = [int(sys.stdin.readline()) for _ in range(H)]

edges = []
for p in P:
    edges.append((p, 'P'))
for q in Q:
    edges.append((q, 'Q'))
edges.sort()

ans = 0
v_nodes = W + 1
h_nodes = H + 1
for e, pq in edges:
    if pq == 'P':
        ans += e * h_nodes
        v_nodes -= 1
    else:
        ans += e * v_nodes
        h_nodes -= 1

print(ans)
