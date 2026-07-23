n=int(input())
a=list(map(int,input().split()))
ans=1
for k in a:
  if k&1:
    ans*=2
print(ans)