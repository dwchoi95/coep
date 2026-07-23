N, M = map(int, input().split())
A = list(map(int, input().split()))



cnt = 0
cnt1 = 0

for i in range(N):
    cnt = cnt + A[i]

for i in range(N):
    if A[i] / cnt > 1 / 4 / M:
        cnt1 = cnt1 + 1



if cnt1 > M:
    print('Yes')
else:
    print('No')
