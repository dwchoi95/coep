N = int(input())
T = list(map(int, input().split()))
A = list(map(int, input().split()))

M = [[-1, 10**9] for i in range(N)]

for i in range(N):
    if i == 0:
        M[i][0] = T[i]
    else:
        if T[i] != T[i-1]:
            M[i][0] = T[i]
        else:
            M[i][1] = T[i]

for i in range(N-1, -1, -1):
    if i == N-1:
        if M[i][0] != -1 and M[i][0] != A[i]:
            print(0)
            exit(0)
        else:
            if M[i][1] >= A[i]:
                M[i][0] = A[i]
            else:
                print(0)
                exit(0)

    else:
        if A[i] != A[i+1]:
            if M[i][0] != -1 and M[i][0] != A[i]:
                print(0)
                exit(0)
            else:
                if A[i] <= M[i][1]:
                    M[i][0] = A[i]
                else:
                    print(0)
                    exit(0)
        else:
            M[i][1] = min(M[i][1], A[i])
ans = 1
mod = (10 ** 9) + 7
for x, y in M:
    if x == -1:
        ans *= y
        ans %= mod

print(ans)
