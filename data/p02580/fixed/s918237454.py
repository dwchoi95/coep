
import sys
from collections import defaultdict

H, W, M = map(int, input().split())
X = [list(map(int, input().split())) for _ in range(M)]

ctr_h = defaultdict(int)
ctr_w = defaultdict(int)
appeared = set()

for h, w in X:
    ctr_h[h] += 1
    ctr_w[w] += 1
    appeared.add(h * W + w)

val_h = sorted(ctr_h.items(), key=lambda x: -x[1])
val_w = sorted(ctr_w.items(), key=lambda x: -x[1])

max_h = val_h[0][1]
max_w = val_w[0][1]

val_h = [i for i, v in val_h if v == max_h]
val_w = [i for i, v in val_w if v == max_w]

if len(val_h) * len(val_w) > M:
    print(max_h + max_w)
    sys.exit(0)

for h in val_h:
    for w in val_w:
        if h * W + w not in appeared:
            print(max_h + max_w)
            sys.exit(0)
else:
    print(max_h + max_w - 1)
