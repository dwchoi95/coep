import sys
import copy
import math
import bisect
import pprint
import bisect
from functools import reduce
from copy import deepcopy
from collections import deque

if __name__ == '__main__':
    a = [int(i) for i in input().split()]
    b = []

    for i in a:
        if i in b:
            b.remove(i)
        else:
            b.append(i)
    print(b[0])