def examA():
    N = I()
    ans = 0
    print(ans)
    return

def examB():
    H, W, N = LI()
    start = LI()
    S = SI(); T = SI()
    for t,a in [["U","D"],["R","L"]]:
        if t=="U":
            n = H
        else:
            n = W
        
        l = 1; r = n
        if S[-1]==t:
            r -=1
        elif S[-1]==a:
            l +=1
        for i in range(N-2,-1,-1):
            if T[i]==t and l>1:
                l -= 1
            elif T[i]==a and r<n:
                r += 1
            if S[i] == t:
                r -= 1
            elif S[i] == a:
                l += 1

            if t=="U" and (r==0 or l==n):
                print("NO")
                return
            if t=="R" and (r==0 or l==n):
                print("NO")
                return

        if t=="U" and (not l<=start[1]<=r):
            print("NO")
            return
        elif t=="R" and (not l<=start[0]<=r):
            print("NO")
            return
    print("YES")
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

