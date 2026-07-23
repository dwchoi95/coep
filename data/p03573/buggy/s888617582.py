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
    bf =999
    for i in a:
        if bf == 999:
            bf =i
        elif bf != i:
            print(i)