N=int(input().rstrip())
a=1
mod=1e9+7
for i in range(1,N+1):
  a*=i
  a%=mod
print(int(a))
