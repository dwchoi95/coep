n = int(input())
a = list(map(int, input().split()))

tmp = []
from collections import Counter
c = Counter(a)
for k in c.keys():
    if c[k] >= 2:
        tmp.append(k)

tmp.sort()
if len(tmp) >= 2:
    print(tmp[-1] * tmp[-2])
else:
    print(0)
