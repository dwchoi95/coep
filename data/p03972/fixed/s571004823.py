import sys
sys.setrecursionlimit(10**7)

readline = sys.stdin.buffer.readline
def readstr():return readline().rstrip().decode()
def readstrs():return list(readline().decode().split())
def readint():return int(readline())
def readints():return list(map(int,readline().split()))
def printrows(x):print('\n'.join(map(str,x)))
def printline(x):print(' '.join(map(str,x)))

import heapq


w,h =readints()
p = [readint() for i in range(w)]
q = [readint() for i in range(h)]

heapq.heapify(p)
heapq.heapify(q)

edge = 0
cost = 0
used = [0,0]

while edge < (h+1)*(w+1)-1:
    if p and q:
        if p[0]<q[0]:
            flag = 1
        else:
            flag = 0
    elif p:
        flag = 1
    else:
        flag = 0
    if flag:
        x = heapq.heappop(p)
        edge += h+1-used[1]
        cost += x * (h+1-used[1])
        used[0] += 1
    else:
        x = heapq.heappop(q)
        edge += w+1-used[0]
        cost += x * (w+1-used[0])
        used[1] += 1

print(cost)








