from collections import deque
N = int(input())

AM, Am, BM, Bm = -1*10**9*2, 10**9*2, -1*10**9*2, 10**9*2
for _ in range(N):
    x, y = map(int, input().split())
    AM = max(AM, x+y)
    Am = min(Am, x+y)
    BM = max(BM, x-y)
    Bm = min(Bm, x-y)


print(max(AM-Am, BM-Bm))