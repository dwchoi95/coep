import math
from bisect import bisect_left, bisect_right

N = int(input())
X = list(map(int, input().split()))
L = int(input())
Q = int(input())
Y = [list(map(int, input().split())) for _ in range(Q)]

LOGN = int(math.log(N) / math.log(2)) + 1
parent = [[-1] * N for _ in range(LOGN + 1)]


for k in range(LOGN + 1):
    for i in range(N):
        if k == 0:
            parent[k][i] = bisect_right(X, X[i] + L) - 1
        else:
            parent[k][i] = parent[k - 1][parent[k - 1][i]]

for a, b in Y:
    a -= 1
    b -= 1
    if a > b:
        a, b = b, a
    i = bisect_left([parent[j][a] for j in range(LOGN + 1)], b)
    print(2 ** i)
