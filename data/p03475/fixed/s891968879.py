n = int(input())
C, S, F = [], [], []
for _ in range(n-1):
    c, s, f = map(int, input().split())
    C.append(c)
    S.append(s)
    F.append(f)

for i in range(n-1):
    t = S[i]
    while i != (n-1):
        if t < S[i]:  
            wait = (S[i] - t)
        else:
            r = (t - S[i])%F[i]
            if r == 0:
                wait = 0 
            else:
                wait = F[i] - r
        t += wait
        t += C[i]  
        i += 1
    print(t)
print(0)  