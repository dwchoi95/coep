
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
d = defaultdict(int)
array = []
for i in range(a):
    x, y = map(int, input().split())
    d[x] = y
    array.append(x)
array.sort()


count = 0
for i in array:
    if b <= d[i]:
        count += max(b, 0) * i
        break
    else:
        t = d[i]
        b -= t
        count += t * i
print(count)