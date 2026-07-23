from collections import Counter, defaultdict
import sys
sys.setrecursionlimit(10 ** 5 + 10)

from math import factorial
import heapq, bisect
import math
import itertools


import queue
from collections import deque




def main():
    high, width = map(int, input().split())
    cost_w = [int(input()) for i in range(width)]
    cost_h = [int(input()) for i in range(high)]

    cost_w.sort()
    cost_h.sort()
    check_high, check_width = 0, 0
    width_ind = 0
    ans = 0
    for i in range(high):

        now_high = cost_h[i]
        while width_ind < width:
            if now_high < cost_w[width_ind]:
                break
            ans += (high + 1 - check_high) * cost_w[width_ind]
            check_width += 1
            width_ind += 1

        ans += (width + 1 - check_width) * cost_h[i]
        check_high += 1

        

    ans += sum(cost_w[width_ind:])

    print(ans)







if __name__ == '__main__':
    main()

