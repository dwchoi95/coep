import bisect
import collections
import copy
import functools
import heapq
import math
import sys
from collections import deque
from collections import defaultdict
input = sys.stdin.readline
MOD = 10**9+7

s = list(input().rstrip())
g = 0
p = 0
res = []
ans = 0

for i in range(len(s)):
    c = g-p
    if s[i] == "g":
        if c > 0:
            
            p += 1
            ans += 1
        else:
            
            g += 1
    else:
        
        p += 1
print(ans)