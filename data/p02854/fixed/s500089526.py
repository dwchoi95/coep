from itertools import accumulate


N = int(input())
A = [0] + list(accumulate(map(int, input().split())))
min_diff = float("inf")
for i in range(N - 1):
    if abs(A[N] - 2 * A[i + 1]) < min_diff:
        min_diff = abs(A[N] - 2 * A[i + 1])
print(min_diff)
