n=int(input())
A=list(map(int,input().rstrip().split(' ')))
Xans=1
for a in A:
  if(a%2==1):
    Xans*=1
  else:
    Xans*=2
    
print(3**n-Xans)
