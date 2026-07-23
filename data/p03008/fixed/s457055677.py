import sys
input = sys.stdin.readline

N = int(input())
ga, sa, ba = map(int, input().split())
gb, sb, bb = map(int, input().split())
INF = 10**18
A = [INF] * 3
B = [INF] * 3
values = [abs(ga - gb), abs(sa - sb), abs(ba - bb)]
if ga < gb:
    A[0] = ga
elif ga > gb:
    B[0] = gb
if sa < sb:
    A[1] = sa
elif sa > sb:
    B[1] = sb
if ba < bb:
    A[2] = ba
elif ba > bb:
    B[2] = bb

def calc(X):
    dp = [0] * (N+1)
    dp[0] = 0
    for x, v in zip(X, values):
        for i in range(N+1-x):
            dp[i+x] = max(dp[i+x], dp[i] + v)
    return dp[-1]

N += calc(A)
N += calc(B)
print(N)