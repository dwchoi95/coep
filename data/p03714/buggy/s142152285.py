def examD():
    N = I()
    a = LI()
    a_b = list(map(lambda x: x*(-1), a))
    R = a[:N]; B = a_b[2*N:]
    heapq.heapify(R)
    heapq.heapify(B)
    ansC =[]
    curR = [sum(R)]; curB = [-sum(B)]
    for i in range(N):
        heapq.heappush(R, a[N+i])
        cur = curR[-1] - heapq.heappop(R) + a[N+i]
        curR.append(cur)
    for i in range(N):
        heapq.heappush(B, a_b[2*N-1-i])
        cur =curB[-1] - heapq.heappop(B)*(-1) - a_b[2*N-1-i]
        curB.append(cur)
    for i in range(N):
        ansC.append(curR[i]-curB[-1-i])
    ans = max(ansC)
    print(ans)




import sys
import copy
import bisect
import heapq
from collections import Counter,defaultdict,deque
def I(): return int(sys.stdin.readline())
def LI(): return list(map(int,sys.stdin.readline().split()))
def LS(): return sys.stdin.readline().split()
def S(): return sys.stdin.readline().strip()
mod = 10**9 + 7
inf = float('inf')

examD()
