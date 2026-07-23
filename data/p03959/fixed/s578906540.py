N = int(input())
T = list(map(int, input().split()))
A = list(map(int, input().split()))


x = [1 for _ in range(N)]
for i in range(1, N):
    if i == 0:
        x[i] = 1
    elif T[i - 1] < T[i]:
        x[i] = 1
    else:
        x[i] = T[i]

y = [1 for _ in range(N)]
for i in range(N - 2, -1, -1):
    if i == N - 1:
        y[i] == 1
    if A[i] > A[i + 1]:
        y[i] = 1
    else:
        y[i] = A[i]

ans = 1

for i in range(N):
    ans = ans * min(x[i], y[i]) % int(1e9 + 7)


for x,y,t,a in zip(x,y,T,A):
    if x == 1 and t > a:
        ans = 0
    if y == 1 and t < a:
        ans = 0


print(ans)