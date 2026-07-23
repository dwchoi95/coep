N, M = map(int, input().split())

A = []
for i in range(N):
    a, b = map(int, input().split())
    A.append([a, b])

A.sort(key=lambda x:x[0])

money = 0
cnt = 0
for i in range(N):
    if cnt + A[i][1] < M: 
        money += A[i][0]*A[i][1]
        cnt += A[i][1]
    else: 
        money += A[i][0]*(M-cnt)
        print(money)
        break