def gcd(a,b):
  a = int(a)
  b = int(b)
  r = (int)(a%b)
  while(r!=0):
    a=(int)(b)
    b=(int)(r)
    r=(int)(a%b)
  return b
def lcm(a,b):
    return int((a*b)
n = int(input())
ans = int(input())
for i in range(n-1):
  num = int(input())
  ans = lcm(max(ans,num),min(ans,num))
print(int(ans))
