N = int(input())
T = list(map(int, input().split(" ")))
A = list(map(int, input().split(" ")))
h = [-1 for i in range(N)]
mod = 10 ** 9 + 7

h[0] = T[0]
h[N - 1] = A[N - 1]
for i in range(N - 1):
    if T[i] < T[i + 1]:
        h[i + 1] = T[i + 1]

for i in range(N - 1):
    if A[i + 1] < A[i] and (h[i] == -1 or h[i] == A[i]):
        h[i] = A[i]
    elif A[i + 1] < A[i]:
        h[i] = 0

ans = 1
for i in range(N):
    if h[i] == 0:
        ans *= h[i]
        break
    elif h[i] == -1:
        ans *= min(T[i], A[i])
        ans %= mod

if A[N - 1] != T[0]:
    print(0)
else:
    print(ans % mod)