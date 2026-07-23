n = int(input())
ans = 0
for i in range(2, 10):
  for j in range(2, 10):
    if i * j == n:
      ans += 1
if ans >= 1:
  print("Yes")
else:
  print("No")