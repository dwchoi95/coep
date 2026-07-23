def examA():
    N = I()
    ans = 0
    print(ans)
    return


def examB():
    H, W, N = LI()
    sr, sc = LI()
    S = SI()
    T = SI()

    sr = H + 1 - sr

    
    L, R = 1, W
    D, U = 1, H
    for s, t in zip(S[::-1], T[::-1]):
        if t == 'L':
            R += 1
        elif t == 'D':
            U += 1
        elif t == 'R':
            L -= 1
        elif t == 'U':
            D -= 1

        if L == 0: L = 1
        if D == 0: D = 1
        if R > W: R = W
        if U > H: U = H

        if s == 'L':
            L += 1
        elif s == 'R':
            R -= 1
        elif s == 'D':
            D += 1
        elif s == 'U':
            U -= 1

        if L > R or D > U:
            
            break

    bl = (L <= sc <= R) and (D <= sr <= U)
    answer = 'YES' if bl else 'NO'
    print(answer)
    return

def examC():
    ans = 0
    print(ans)
    return

def examD():
    ans = 0
    print(ans)
    return

import sys,copy,bisect,itertools,heapq,math
from heapq import heappop,heappush,heapify
from collections import Counter,defaultdict,deque
def I(): return int(sys.stdin.readline())
def LI(): return list(map(int,sys.stdin.readline().split()))
def LSI(): return list(map(str,sys.stdin.readline().split()))
def LS(): return sys.stdin.readline().split()
def SI(): return sys.stdin.readline().strip()
global mod,mod2,inf,alphabet
mod = 10**9 + 7
mod2 = 998244353
inf = 10**18
alphabet = [chr(ord('a') + i) for i in range(26)]

if __name__ == '__main__':
    examB()

