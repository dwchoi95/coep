
from collections import defaultdict

H, W, M = map(int, input().split())
X = [list(map(int, input().split())) for _ in range(M)]

ctr_h = defaultdict(list)
ctr_w = defaultdict(list)

for h, w in X:
    ctr_h[h].append((h, w))
    ctr_w[w].append((h, w))

val_h = sorted(ctr_h.items(), key=lambda x: -len(x[1]))
val_w = sorted(ctr_w.items(), key=lambda x: -len(x[1]))

max_h = len(val_h[0][1])
max_w = len(val_w[0][1])

if (len(val_h) > 1 and len(val_h[1][1]) == max_h
        and len(val_w) > 1 and len(val_w[1][1]) == max_w):
    print(max_h + max_w)
else:
    h = val_h[0][0]
    w = val_w[0][0]
    for u, v in X:
        if u == h and v == w:
            print(max_h + max_w - 1)
            break
    else:
        print(max_h + max_w)
