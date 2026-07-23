from math import *
import fractions
import sys
import collections
import itertools
import pprint
from collections import deque
from heapq import *
import copy
N=int(input())
points=[list(map(int,input().split())) for _ in range(N)]


chebmax0=-float("inf")
chebmin0=float("inf")
chebmax1=-float("inf")
chebmin1=float("inf")


for l in points:
    chebmax0=max(chebmax0,l[0]-l[1])
for l in points:
    chebmin0=min(chebmax0,l[0]-l[1])
for l in points:
    chebmax1=max(chebmax1,l[0]+l[1])
for l in points:
    chebmin1=min(chebmax1,l[0]+l[1])

print(max(chebmax0-chebmin0,chebmax1-chebmin1))