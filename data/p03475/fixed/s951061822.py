
N = int(input())
C = []
S = []
F = []
for i in range(N-1):
    Ci, Si, Fi = list(map(int, input().split((" "))))
    C.append(Ci)
    S.append(Si)
    F.append(Fi)

ans = []
for i in range(N):
    t = 0
    for j in range(i, N-1):
        if t < S[j]:
            t = S[j]
        elif t % F[j] == 0:
            pass
        else:
            t = t + F[j] - (t % F[j])
        t += C[j]
    print(t)

