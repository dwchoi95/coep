N, M = map(int, input().split())

A = []
for i in range(N):
    a, b = map(int, input().split())
    A.append([a, b])

A.sort(key=lambda x:x[0])

money = 0
cnt = 0
for i in range(N):
    for j in range(A[i][1]):
        money += A[i][0]
        if cnt == N:
            print(money)
            break