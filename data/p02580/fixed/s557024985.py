import sys
import bisect
import itertools
import collections
import fractions
import heapq
import math
from operator import mul
from functools import reduce
from functools import lru_cache


def solve():
    readline = sys.stdin.buffer.readline
    input = readline
    mod = 10 ** 9 + 7
    H, W, M = map(int, input().split())
    Hlist = collections.defaultdict(int)
    Wlist = collections.defaultdict(int)
    hw = []

    for _ in range(M):
        h, w = map(int, input().split())
        Hlist[h-1] += 1
        Wlist[w-1] += 1
        hw.append([h, w])

    
    

    Hlist = sorted(Hlist.items(), key=lambda x: x[1], reverse=True)
    Wlist = sorted(Wlist.items(), key=lambda x: x[1], reverse=True)

    hmaxset = set()
    wmaxset = set()

    maxH = Hlist[0][1]
    for k, v in Hlist:
        if v != maxH:
            break
        else:
            hmaxset.add(k)

    maxW = Wlist[0][1]
    for k, v in Wlist:
        if v != maxW:
            break
        else:
            wmaxset.add(k)


    flag = False
    count = 0
    for hh in hw:
        h = hh[0] - 1
        w = hh[1] - 1
        if h in hmaxset and w in wmaxset:
            count += 1

    lenhmax = len(hmaxset)
    lenwmax = len(wmaxset)

    if count != lenhmax * lenwmax:
        flag = True

    if flag:
        print(maxH + maxW)
    else:
        print(maxH + maxW - 1)





if __name__ == '__main__':
    solve()