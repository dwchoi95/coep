
import sys
from math import floor
sys.setrecursionlimit(100000)

N = int(input())
heap = [None] + [int(n) for n in input().split()]

for i, h in enumerate(heap[1:]):
    i += 1
    text = "node {}: key = {}".format(i, h)
    if i != 1:
        text += ", parent key = {}".format(heap[floor(i/2)])
    if 2 * i <= N:
        text += ", left key = {}".format(heap[2*i])
    if 2 * i + 1 <= N:
        text += ", right key = {}".format(heap[2*i + 1])
    print(text)