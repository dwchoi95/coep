a,b,k=map(int,input().split())
temp=[]
for i in range(1,min(a,b)+1):
  if a%i==0 and b%i==0:
    temp.append(i)
print(temp[k-1])
  