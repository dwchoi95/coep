import os
import sys
import heapq


def solve(n, a):
    res = -10 ** 20
    for i in range(n, 2 * n + 1):
        l = a[0:i]
        r = a[i:3 * n]
        l.sort(reverse=True)
        r.sort()
        res0 = sum(l[0:n]) - sum(r[0:n])
        if res0 > res:
            res = res0
    return res


def find_best(n, a):
    h = list()
    s = 0
    best_s = -10**20
    res = list()
    for i in range(0, 2 * n):
        heapq.heappush(h, a[i])
        s += a[i]
        if len(h) > n:
            m = heapq.heappop(h)
            s -= m
        if len(h) == n:
            if best_s < s:
                best_s = s
            res.append(best_s)
    return res


def solve_large(n, a):
    res = -10 ** 20
    max_l = find_best(n, a)
    b = [-x for x in reversed(a)]
    max_r = find_best(n, b)
    max_r.reverse()
    for l, r in zip(max_l, max_r):
        res0 = l + r
        if res < res0:
            res = res0
    return res


input_file = 'd1.in'
if os.path.exists(input_file):
    sys.stdin = open(input_file)
n = int(input())
a = list(map(int, input().split()))
print(solve_large(n, a))
