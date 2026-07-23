
N = int(input())
T = []
for i in range(N):
  T.append(int(input()))

def gcd(a,b): 
  if min(a,b) == 0:
    return max(a,b)
  else:
    return gcd(min(a,b),max(a,b)%min(a,b))
    



def lcm(a,b):
  
  g = gcd(a,b)
  
  return int(a*b
ans = T[0]
for i in range(1,len(T)):
  ans = lcm(ans,T[i])
print(ans)
