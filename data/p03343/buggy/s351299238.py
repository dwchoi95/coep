N, K, Q = [int(i) for i in input().split()]
A = [(int(v),i) for i,v in enumerate(input().split())]
A.sort()
B = [0]*(N)
for i in range(N):
    B[A[i][1]] = i
C = [A[B[i]][0] for i in range(N)]
Candi = set(range(N))
ctr = 0
ans = []
while len(Candi) >= Q:
    ans.append((list(Candi)[0],list(Candi)[Q-1]))
    x = B.index(ctr)
    Candi = Candi - set(B[x-K+1:x+K])
    ctr += 1
print(min([A[j][0]-A[i][0] for i,j in ans]))
