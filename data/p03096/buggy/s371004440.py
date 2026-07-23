import sys
import math
import collections
import bisect
import copy



sys.setrecursionlimit(10 ** 9)
INF = 10 ** 16
MOD = 10 ** 9 + 7


ni = lambda: int(sys.stdin.readline())
ns = lambda: map(int, sys.stdin.readline().split())
na = lambda: list(map(int, sys.stdin.readline().split()))
na1 = lambda: list(map(lambda x: int(x) - 1, sys.stdin.readline().split()))





def main():
    n = ni()
    idxlist = [[] for _ in range(2 * 10 ** 5 + 1)]
    d = []
    dp = [INF for _ in range(n + 1)]
    dp[0] = 1

    for i in range(n):
        di = ni()
        di -= 1
        if i > 0:
            if d[-1] == di:
                d.append(-1)
                continue
        d.append(di)
        idxlist[di].append(i)

    for i, di in enumerate(d):
        
        dp[i + 1] = dp[i]
        if di == -1:
            continue
        bidx = bisect.bisect_left(idxlist[di], i)
        if bidx - 1 >= 0:
            dp[i + 1] += dp[idxlist[di][bidx - 1] + 1]
            dp[i + 1] %= MOD

    print(dp[n])


if __name__ == '__main__':
    main()
