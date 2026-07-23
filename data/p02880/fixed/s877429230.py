n = int(input())
ans = 0
for i in range(1, 10):
  for j in range(1, 10):
    if i * j == n:
      ans += 1
if ans == 0:
  print("No")
else:
  print("Yes")