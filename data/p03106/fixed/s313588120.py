
def gcd(a,b):
    if b == 0:return a
    return gcd(b,a%b)

a,b,k = map(int,input().split())

g = gcd(a,b)

cnt = 0
for i in range(g,0,-1):
  if a%i == 0 and b%i == 0:
    
    cnt+=1
    if cnt == k:
      print(i)
      break
