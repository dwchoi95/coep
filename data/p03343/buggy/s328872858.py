N, K, Q = map(int, input().split())
X = list(map(int, input().split()))
Y = sorted(X)





r = Y[Q-1] - Y[0]
for y in Y[1:]:
    tmp = []
    tmp2 = []
    for x in X:
        if x < y:
            tmp.sort()
            tn = len(tmp)
            if tn-K+1 > 0:
                tmp2 += tmp[:tn-K+1]
            tmp = []
            continue
        tmp.append(x)
    tn = len(tmp)
    if tn-K+1 > 0:
        tmp2 += tmp[:tn-K+1]
    tmp2.sort()
    if len(tmp2) >= Q:
        r = min(r, tmp2[Q-1] - y)
print(r)
