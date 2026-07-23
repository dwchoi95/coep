a,b,k=list(map(int,input().split()))
cnt=1
for i in range(1,min(a,b)+1):
  if a%i==0 and b%i==0:
    if cnt==k:
      print(i)
      break
    cnt+=1