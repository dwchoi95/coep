import sys
from collections import Counter, deque, defaultdict
from math import factorial
import heapq, bisect
import math
import itertools
sys.setrecursionlimit(10 ** 5 + 10)
INF = 10*5
def input(): return sys.stdin.readline().strip()
def INT(): return int(input())
def MAP(): return map(int, input().split())
def LIST(): return list(map(int, input().split()))

def main():
    n = INT()
    a = LIST()

    a1 = a[:2*n]
    a2 = a[n:]
    a2.reverse()
    for i in range(2*n):
        a2[i] = a2[i]*-1

    def searchmax(a):
        maxl = [0]*(n+1)
        left = a[:n]
        center = a[n:]
        heapq.heapify(left)
        maxl[0] = sum(left)
        for i in range(1,n+1):
            poped = heapq.heappushpop(left, center[i-1])
            maxl[i] = max(maxl[i-1], maxl[i-1]-poped+center[i-1])
        return maxl

    maxll = searchmax(a1)
    minrr = searchmax(a2)
    minrr.reverse()

    res = [INF *-1]*(n+1)
    for i in range(n+1):
        res[i] = maxll[i] + minrr[i]

    print(max(res)) 

if __name__ == '__main__':
    main()
    

