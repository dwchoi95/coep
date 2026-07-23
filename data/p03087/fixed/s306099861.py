from itertools import accumulate

n, q = map(int, input().split())

s = input()

problems = [list(map(int, input().split())) for _ in range(q)]


def count(total, i):
    return total + 1 if s[i:i+2] == 'AC' else total


cumsum = list(accumulate([0] + list(range(n)), count))

for l, r in problems:
    print(cumsum[r-1] - cumsum[l-1])

