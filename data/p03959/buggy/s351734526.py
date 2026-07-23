mod = 10 ** 9 + 7

N = int(input())
T = [0] + list(map(int, input().split()))
A = list(map(int, input().split())) + [0]

H = [0] * N
for i in range(1, N):
    if T[i - 1] < T[i]:
        H[i - 1] = T[i]
for i in range(N - 1, -1, -1):
    if A[i + 1] < A[i]:
        if H[i] == 0 or H[i] == A[i]:
            H[i] = A[i]
        else:
            print(0)
            exit()

ans = 1
T.pop(0)
A.pop(-1)
for h, t, a in zip(H, T, A):
    if h == 0:
        ans *= min(t, a)
        ans %= mod
print(ans)