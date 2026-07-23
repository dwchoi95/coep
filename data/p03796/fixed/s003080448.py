n=int(input())
sum=1
for i in range(n):
  sum*=i+1
  if sum>10**9:
    sum=sum%(10**9+7)
  
print(sum)