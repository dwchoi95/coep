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
    Hlist = [0] * H
    Wlist = [0] * W
    hw = []

    for _ in range(M):
        h, w = map(int, input().split())
        Hlist[h-1] += 1
        Wlist[w-1] += 1
        hw.append([h, w])


    hmax = [i for i, x in enumerate(Hlist) if x == max(Hlist)]
    wmax = [i for i, x in enumerate(Wlist) if x == max(Wlist)]
    hmaxset = set(hmax)
    wmaxset = set(wmax)

    flag = False
    for hh in hw:
        h = hh[0] - 1
        w = hh[1] - 1
        if not (h in hmaxset and w in wmaxset):
            flag = True
            break


    if flag:
        print(Hlist[h] + Wlist[w])
    else:
        print(Hlist[h] + Wlist[w] - 1)





if __name__ == '__main__':
    solve()