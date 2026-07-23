N, Q = map(int, input().split())
S = str(input())
LR = [list(map(int, input().split())) for _ in range(Q)]

count = [0]*(N)
for i in range(1, N):
    if S[i]=='C' and S[i-1]=='A':
        count[i] = count[i-1] + 1
    else:
        count[i] = count[i-1]
for l, r in LR:
    print(count[r-1]-count[l-1])