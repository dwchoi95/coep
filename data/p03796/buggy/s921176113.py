n=int(input())
for i in range(n):
  n=(n*(i+1))%(10**9+7)
print(n)