
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
d = []
for i in range(a):
    x, y = map(int, input().split())
    d.append((x, y))
d.sort()
count = 0
for i in range(a):
    if b <= d[i][1]:
        count += b * d[i][0]
        break
    else:
        b -= d[i][1]
        count += d[i][0] * d[i][1]
print(count)