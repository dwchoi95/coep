n=int(input())
k=list(map(int,input().split()))
ans=0
for i in range(n):
  for j in range(n):
    if i==j:
      break
    ans+=k[i]*k[j]
print(ans)
