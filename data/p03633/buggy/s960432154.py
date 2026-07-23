import functools
N = int(input())
T = []
for i in range(N):
  T.append(int(input()))

def gcd(a, b):
  if a < b:
    a, b = b, a
  if b == 0:
    return a
  return gcd(b, b % a)
 
def lcm(A, B):
  return A * B 
 
print(functools.reduce(lcm, T))