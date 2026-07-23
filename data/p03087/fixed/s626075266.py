N,Q = [int(i) for i in input().split()]
S=input()
lr = [[int(j)-1 for j in input().split()] for i in range(Q)]

imos = [0 for i in range(N)]
for i in range(N-1):
    if S[i]=='A' and S[i+1]=='C':
        imos[i]=1
for i in range(N-1):
    imos[i+1]+=imos[i]
for l,r in lr:
    res = imos[r]
    if l>0:
        res-=imos[l-1]
    if S[r]=='A' and r<N-1 and S[r+1]=='C':
        res-=1
    print(res)
