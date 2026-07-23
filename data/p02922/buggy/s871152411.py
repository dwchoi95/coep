(A, B), = [list(map(int, s.split())) for s in open(0)]
if A >= B:
    print(1)
else:
    if (B - A)%(A - 1) == 0:
        print(int((B - A)/(A - 1) + 1))
    else:
        t = (B - A)
        while A + (A - 1)*(t - 1) < B:
            t += 1
        print(int(t))