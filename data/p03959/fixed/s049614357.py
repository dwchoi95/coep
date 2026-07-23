N = int(input())
T = list(map(int, input().split(" ")))
A = list(map(int, input().split(" ")))
h = [0 for i in range(N)]
mod = 10 ** 9 + 7

h[0] = T[0]
for i in range(N - 1):
    if T[i] < T[i + 1]:
        h[i + 1] = T[i + 1]
    else:
        h[i + 1] = -T[i + 1]

if h[N - 1] == 0:
    h[N - 1] = A[N - 1]
else:
    if -h[N - 1] >= A[N - 1]:
        h[N - 1] = A[N - 1]
    elif h[N - 1] != A[N - 1]:
        h[N - 1] = 0

for i in range(1, N):
    if A[i - 1] > A[i]:
        if -h[i - 1] >= A[i - 1]:
            h[i - 1] = A[i - 1]
        elif h[i - 1] != A[i - 1]:
            h[i - 1] = 0
    else:
        if h[i - 1] < 0:
            h[i - 1] = -min(-h[i - 1], A[i - 1])


ans = 1
for hi in h:
    if hi <= 0:
        ans *= -hi
        ans %= mod

print(ans)