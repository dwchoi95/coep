
N = int(input())
T = []
for i in range(N):
  T.append(int(input()))

def gcd(a,b):
  mi = min(a,b)
  ma = max(a,b)
  ans = 1
  
  while True:
    print(ma,mi)
    if (ma % mi) == 0:
      ans = mi
      break
    else:
      mi = ma%mi
      ma = mi
      
  return ans



def lcm(a,b):
  
  g = gcd(a,b)
  print(g)
  return int(a*b/g)
ans = T[0]
for i in range(1,len(T)):
  ans = lcm(ans,T[i])
print(ans)
