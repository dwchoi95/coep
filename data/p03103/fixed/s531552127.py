

N, M = map(int, input().split())

A = [list(map(int, input().split())) for i in range(N)]
A = sorted(A)

ans = 0
m = M
for a, b in A:
    if m <= b:
        ans += m*a
        break
    else:
        ans += b*a
        m -= b

print(ans)
