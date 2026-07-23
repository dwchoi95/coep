N = int(input())
T = [int(input()) for i in range(N)]

def gcd(m,n):
  x = max(m,n)
  y = min(m,n)
  if x%y == 0:
    return y
  else:
    while x%y != 0:
      z = x%y
      x = y
      y = z
    else:
      return z

def lcm(m,n):
  return int(m * n 

ans = 1
for i in range(N):
    ans = lcm(T[i], ans)

print(ans)