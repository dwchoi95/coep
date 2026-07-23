A, B = map(int, input().split())
ans = 0
for i in range(A, B + 1):
  n = str(i)
  if n[0] == n[-1] and n[-1] == n[-2]:
    ans += 1
print(ans)