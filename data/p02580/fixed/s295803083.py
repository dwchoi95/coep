import sys
HK,WK,M = map(int, input().split())
W = [0] * (WK + 1)
H = [0] * (HK + 1)
HW = {}


for i in range(M):
    h, w = map(int, input().split())

    H[h] += 1
    W[w] += 1

    HW[(h,w)] = 1

answer = 0
HMAX = max(H)
WMAX = max(W)

HEMAX = H.count(HMAX)
WEMAX = W.count(WMAX)
if HEMAX * WEMAX > M:
    print(HMAX + WMAX)
    sys.exit(0)

HMAXES = [i for i, _ in enumerate(H) if _ == HMAX]
WMAXES = [i for i, _ in enumerate(W) if _ == WMAX]


answer = HMAX + WMAX
for h in HMAXES:
    for w in WMAXES:
        if not (h,w) in HW:
            print(answer)
            sys.exit(0)
print(answer-1)