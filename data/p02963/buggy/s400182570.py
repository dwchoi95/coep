
import sys
sys.setrecursionlimit(12345678)
import itertools
from collections import Counter
from collections import defaultdict
from collections import deque
import bisect
from heapq import heappush, heappop


def main():
    s = int(input())
    x1, y1, x2, y2 = 0, 0, 10 ** 9, 1

    y3, x3 = divmod(s, 10**9)

    print(x1, y1, x2, y2, x3, y3)

if __name__ == '__main__':
    main()
