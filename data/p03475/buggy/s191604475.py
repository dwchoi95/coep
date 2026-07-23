N = int(input())
C = []
S = []
F = []
for i in range(N-1):
    c, s, f = map(int, input().split())
    C.append(c)
    S.append(s)
    F.append(f)

for i in range(0, N-1):
    t = S[i]
    for j in range(i, N-1):
        if t <= S[j]:
            t = S[j]
        else:
            t += F[j] - t%F[j]
        t += C[j]
    print(t)
print(0)