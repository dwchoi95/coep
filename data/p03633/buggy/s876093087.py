def gcd(a,b):
  r = a%b
  while(r!=0):
    a=b
    b=r
    r=a%b
  return b
def lcm(a,b):
    return (a*b)/gcd(a,b)
n = int(input())
ans = int(input())
for i in range(n-1):
  num = int(input())
  ans = lcm(max(ans,num),min(ans,num))
print(int(ans))
