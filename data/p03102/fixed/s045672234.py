N,M,C = map(int,input().split())
B = input().split()
Anm = []
for i in range(N):
    Anm.append(input().split())
cont = 0
for A in Anm:
    c = C
    for i in range(M):
        c += int(A[i]) * int(B[i])
    if c > 0:
        cont += 1
print(cont)