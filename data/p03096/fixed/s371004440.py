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
    last = [-1 for _ in range(2 * 10 ** 5 + 1)]
    dp = [INF for _ in range(n + 1)]
    dp[0] = 1

    d = [ni()-1 for _ in range(n)]

    for i, di in enumerate(d):
        dp[i + 1] = dp[i]
        if last[di] != -1:
            if i - last[di] != 1:
                dp[i + 1] += dp[last[di] + 1]
                dp[i + 1] %= MOD
        last[di] = i

    print(dp[n])


if __name__ == '__main__':
    main()
