(A, B), = [list(map(int, s.split())) for s in open(0)]

if B == 1:
    print(0)
elif A >= B:
    print(1)
else:
    cnt = 1
    while True:
        if B <= A + (A - 1)*(cnt - 1):
            break
        cnt += 1
    print(cnt)