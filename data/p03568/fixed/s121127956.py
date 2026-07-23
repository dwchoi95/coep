n=int(input())
a=list(map(int,input().split()))
ans=1
for k in a:
  if k%2==0:
    ans*=2
print(pow(3,n)-ans)