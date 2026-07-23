
import sys
from collections import deque, defaultdict
import copy
import bisect

import math
import heapq
from itertools import combinations, permutations

import sys
def input():
	return sys.stdin.readline().strip()

N = int(input())
a = list(map(int, input().split()))

a_max = a[:N]
a_min = a[2*N:]

a_max_sum = sum(a_max)
score = [a_max_sum]
heapq.heapify(a_max)
for i in range(N):
	heapq.heappush(a_max, a[N + i])
	a_max_sum += a[N + i]
	a_max_sum -= heapq.heappop(a_max)
	score.append(a_max_sum)

a_min_sum = sum(a_min)
score[N] -= a_min_sum
for i in range(len(a_min)):
	a_min[i] *= -1
heapq.heapify(a_min)
for i in range(N):
	heapq.heappush(a_min, -a[2*N - 1 - i])
	a_min_sum += a[2*N - 1 - i]
	a_min_sum += heapq.heappop(a_min)
	score[N - i - 1] -=a_min_sum

print(max(score))