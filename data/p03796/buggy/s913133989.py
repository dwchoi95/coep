n = int(input())
ans = 1
for i in range(1,n):
  ans *= i
  ans %= 10**9 + 7
print(ans)