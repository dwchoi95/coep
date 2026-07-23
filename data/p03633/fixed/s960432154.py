import functools
N = int(input())
T = []
for i in range(N):
  T.append(int(input()))
def gcd(A, B):
  while(True):
    if A and B:
      if A > B:
        A = A % B
      else:
        B = B % A
    else:
      return max(A, B)
 
def lcm(A, B):
  return (A 
 
print(functools.reduce(lcm, sorted(T, reverse=True)))