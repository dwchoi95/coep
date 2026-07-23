ans=0
n=int(input())
li=list(map(int,input().split()))
for i in range(len(li)):
  for j in range(len(li)):
    if i==j:
      break
    ans+=li[i]*li[j]
print(ans)
