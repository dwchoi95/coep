n=int(input())
sum=1
for i in range(n):
  sum*=i
  sum=sum%(10**9+7)
  
print(sum)