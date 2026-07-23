import sys
input = sys.stdin.readline
from itertools import accumulate

W, H = map(int,input().split())

P = [int(input()) for _ in range(W)]
Q = [int(input()) for _ in range(H)]

P.sort()
Q.sort()

cum_p = [0] + list(accumulate(P))
cum_q = [0] + list(accumulate(Q))

res = 0

N = min(len(cum_p), len(cum_q))

for i in range(N):
    res += cum_p[-1 - i] + cum_q[-1 - i]

for i in range(N - 1):
    res += min(P[-1 - i], Q[-1 - i])
    
print(res)