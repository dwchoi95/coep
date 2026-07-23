N = int(input())
B = list(map(int, input().split()))

ans = B[-1]

for i in range(N-2):
    ans += min(B[i],B[i+1])

if N == 2:
    ans += B[0]


print(ans)