mod = 10 ** 9 + 7

N = int(input())
T = list(map(int, input().split()))
A = list(map(int, input().split()))

H = [0] * N
for i in range(N):
    if i == 0 or T[i - 1] < T[i]:
        H[i] = T[i]

for i in range(N - 1, -1, -1):
    if i == N - 1 or A[i] > A[i + 1]:
        H[i] = A[i]
    
ans = 1
for i in range(N):
    if H[i] == 0:
        H[i] = min(T[i], A[i])
        ans *= min(T[i], A[i])
        ans %= mod

flag = True
M = 0
for i in range(N):
    M = max(M, H[i])
    flag &= (M == T[i])
M = 0
for i in range(N - 1, -1, -1):
    M = max(M, H[i])
    flag &= (M == A[i])

if flag is True:
    print(ans)
else:
    print(0)