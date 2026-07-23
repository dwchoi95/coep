a = list(map(int, input().split()))
ans = -float('inf')
for i, v in enumerate(a):
  for j in a[i + 1:]:
    ans = max(ans, v * j)
print(ans)