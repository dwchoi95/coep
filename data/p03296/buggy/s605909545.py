N=int(input())
a=[]
a=input().split()
sum=0

for i in range (1,N-2):
  if a[i-1]==a[i] or a[i+1]==a[i]:
    i=i+1
    sum=sum+1

print(sum)