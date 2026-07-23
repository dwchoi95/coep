n=int(input())
A=list(map(int,input().rstrip().split(' ')))
ans=1
for a in A:
  if(a%2==1):
    ans*=3
    
print(ans)