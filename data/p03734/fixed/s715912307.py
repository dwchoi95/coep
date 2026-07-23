from itertools import accumulate
import heapq

import sys
sys.setrecursionlimit(10**9)
input = sys.stdin.readline

N, W = map(int, input().split())
first_item = list(map(int, input().split()))
basew = first_item[0]
w0 = []
w1 = []
w2 = []
w3 = []
w0.append(first_item[1])
for _ in range(N-1):
    w, v = map(int, input().split())
    w -= basew
    if w == 0:
        w0.append(v)
    elif w == 1:
        w1.append(v)
    elif w == 2:
        w2.append(v)
    elif w == 3:
        w3.append(v)

w0_acc = [0]+list(accumulate(sorted(w0, reverse=True)))
w1_acc = [0]+list(accumulate(sorted(w1, reverse=True)))
w2_acc = [0]+list(accumulate(sorted(w2, reverse=True)))
w3_acc = [0]+list(accumulate(sorted(w3, reverse=True)))
v = 0
for i0 in range(len(w0)+1):
    for i1 in range(len(w1)+1):
        for i2 in range(len(w2)+1):
            for i3 in range(len(w3)+1):
                if basew*(i0+i1+i2+i3)+3*i3 + 2*i2 + i1 > W:
                    break
                else:
                    v = max(v, w0_acc[i0]+w1_acc[i1]+w2_acc[i2]+w3_acc[i3])
print(v)
