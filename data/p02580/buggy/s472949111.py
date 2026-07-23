


from math import gcd
from itertools import combinations,permutations,accumulate, product 

from collections import deque,defaultdict,Counter
import decimal
import re
import math
import bisect
import heapq














import sys
sys.setrecursionlimit(10000000)
mod = 10**9 + 7


INF = float('inf')
from sys import stdin
readline = stdin.readline
def readInts():
  return list(map(int,readline().split()))
def readTuples():
    return tuple(map(int,readline().split()))
def I():
    return int(readline())
H,W,M = readInts()

dic1 = defaultdict(int)
dic2 = defaultdict(int)
s = set()
for i in range(M):
    h,w = map(lambda x:int(x)-1, input().split())
    dic1[h] += 1
    dic2[w] += 1
    s.add((h,w))


ans = 0






for h,w in s:
    ans = max(ans, dic1[h] + dic2[w] - 1)

max1 = max(dic1, key = dic1.get)
max2 = max(dic2, key = dic2.get)
if (max1,max2) in s:
    pass
else:
    ans = max(ans, dic1[max1] + dic2[max2])
print(ans)
