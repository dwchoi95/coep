from itertools import groupby

S = list(input())
n = len(S)
s = [len(list(j)) for i, j in groupby(S)]
s = [max(i, n - i) for i in s]

print(min(s))
