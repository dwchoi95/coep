n = int(input())
r = 1
w = 10**9 + 7
for i in range(1, n+1):
  if r > w:
    r = (r % w) * i
  else:
    r *= i
  
  
print(r)