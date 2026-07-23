N = int(input())
s = 1
for i in range(1, N+1):
  s *= i
  s %= (7 + 1E+9)
print(s)