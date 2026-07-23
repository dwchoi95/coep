
import sys

import heapq
import re
import bisect
import random
import math
import itertools
from collections import defaultdict, deque
from copy import deepcopy
from decimal import *

a, b = map(int, input().split())
d = defaultdict(list)
array = []
for i in range(a):
    x, y = map(int, input().split())
    d[x].append(y)
    array.append(x)
array.sort()
count = 0
for i in array:
    if b <= d[i][0]:
        count += max(b, 0) * i
        break
    else:
        t = d[i][0]
        b -= t
        count += t * i
    d[i].pop()
print(count)