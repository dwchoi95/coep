n = int(input())
d = list(map(int, input().split()))
ans = 0
for i in range(n - 1):
  for j in range(i + 1, n):
    print(i, j)
    ans += d[i] * d[j]
print(ans)
    