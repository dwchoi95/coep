from itertools import accumulate

n, q = map(int, input().split())

s = input()

problems = [list(map(int, input().split())) for _ in range(q)]


def count(total, i):
    return total + 1 if s[i-1] + s[i] == 'AC' else total


cumsum = [0] + list(accumulate(range(1, n), count))

for l, r in problems:
    print(cumsum[r-1] - cumsum[l-1])

