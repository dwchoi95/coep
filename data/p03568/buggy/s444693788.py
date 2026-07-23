n=int(input())
a=list(map(int,input().split()))
f=1
for i in a:
  if i&1:
    f=0
print(3**n-1-f)