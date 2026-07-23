import sys
input = sys.stdin.readline
from bisect import bisect_left, bisect_right

W, H = map(int,input().split())

P = [int(input()) for _ in range(W)]
Q = [int(input()) for _ in range(H)]

P.sort()
Q.sort()

res = 0

for i in range(W):
    res += (H + 1 - bisect_left(Q, P[i])) * P[i]

for i in range(H):
    res += (W + 1 - bisect_right(P, Q[i])) * Q[i]
    
print(res)