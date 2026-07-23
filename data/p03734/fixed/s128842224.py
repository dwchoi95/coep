from itertools import accumulate

N, W = map(int, input().split())
d = {i: [] for i in range(4)}
for i in range(N):
    w, v = map(int, input().split())
    if i == 0:
        w0 = w
    w -= w0
    d[w].append(v)

wv = [[] for _ in range(4)]
for k, v in d.items():
    v.sort(reverse=True)
    v = [0] + v
    wv[k] = tuple(accumulate(v))



ans = 0
for c0, v0 in enumerate(wv[0]):
    for c1, v1 in enumerate(wv[1]):
        for c2, v2 in enumerate(wv[2]):
            for c3, v3 in enumerate(wv[3]):
                weight = w0 * (c0 + c1 + c2 + c3) + c1 + c2 * 2 + c3 * 3
                val = v0 + v1 + v2 + v3
                if weight > W:
                    continue
                ans = max(ans, val)

print(ans)
