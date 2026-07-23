N=int(input())
li=[0]*(10**6+1)
flag=False
for i in range(2,int(N**0.5)+1):
  while N%i==0:
    flag=True
    N/=i
    li[i]+=1
if flag==False:
  print(1)
  exit()
ans=0
for count in li:
  use=1
  while count-use>=0:
    ans+=1
    count-=use
    use+=1
print(ans)
    
    