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
            wait = (t - S[i])%F[i]
        t += wait
        move = C[i]
        t += move
        i += 1
    print(t)
print(0)  