N = int(input())
A = list(map(int, input().split()))

ans = 0
pr = -1
for i in range(1, N):
    if A[i - 1] == A[i]:
        ans += 1
        A[i] = pr
        pr -= 1

print(ans)