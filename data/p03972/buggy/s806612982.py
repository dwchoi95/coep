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

P.sort(reverse=True)
Q.sort(reverse=True)

ans = 0
v_nodes = W + 1
h_nodes = H + 1
while P or Q:
    if not Q or (P and P[-1] < Q[-1]):
        ans += P.pop() * h_nodes
        v_nodes -= 1
    else:
        ans += Q.pop() * v_nodes
        h_nodes -= 1
print(ans)
