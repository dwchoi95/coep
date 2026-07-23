n = int(input())

res = 1

for i in range(1, n):
  res = res*i%(10**9+7)

print(res)