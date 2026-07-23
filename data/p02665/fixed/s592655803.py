N = int(input())
A = list(map(int, input().split()))
B = [0] *(N+1)
B[0] = 1
ans = 0
for i in range(1, N+1):
    B[i] = (B[i-1] - A[i-1])*2
    if B[i] <= 0:
        ans = -1
        break
if B[N] < A[N]:
    ans = -1
if ans == 0:
    check = 0
    for j in range(N, 0, -1):
        check += A[j]
        if check < B[j]:
            ans += check
        else:
            last = j
            for k in range(1, last+1):
                ans += B[k]
            break
    ans += 1
if N == 0 and A[0] == 1:
    ans = 1
print(ans)
