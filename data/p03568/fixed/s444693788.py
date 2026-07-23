n=int(input())
a=list(map(int,input().split()))
f=1
for i in a:
  if i%2==0:
    f<<=1
print(3**n-f)