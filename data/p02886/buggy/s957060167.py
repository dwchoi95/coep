ans=0
n=int(input())
li=list(map(int,input().split()))
for i in li:
  for j in li:
    if i==j:
      break
    ans+=i*j
print(ans)
