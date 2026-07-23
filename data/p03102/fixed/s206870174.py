n, m, c = map(int, input().split())
b = list(map(int, input().split()))
a = [list(map(int, input().split())) for i in range(n)]

ans = 0
for i in range(n):
  s = sum([a[i][j]*b[j] for j in range(m)])
  if s+c > 0:
    ans += 1
print(ans)