N = int(input())
T = [int(input()) for i in range(N)]

dvs = []
dvs_all = []

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
  return m * n / gcd(m,n)

if N == 1:
  ans = T[0]
else:
  for i in range(N - 1):
    T[i+1] = lcm(T[i], T[i+1])
    ans = T[i+1]

print(ans)