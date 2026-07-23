


import sys
import math
import bisect
sys.setrecursionlimit(1000000000)
from heapq import heappush, heappop
from collections import defaultdict
from itertools import accumulate
from collections import Counter
from collections import deque
from operator import itemgetter
from itertools import permutations
mod = 10**9 + 7

s = input()
n = len(s)
ans = 0
cnt = 0
for i in range(n):
    if s[i] == 'g':
        if cnt > 0:
            ans += 1
            cnt -= 1
        else:
            cnt += 1
    else:
        cnt -= 1
print(ans)
