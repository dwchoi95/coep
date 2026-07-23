N=int(input())
list = list(map(int, input().split()))
c=100
l=len(list)
m=0
k=0
i=0
while(k<l):
  m+=(list[k]-1)**2
  k+=1
j=1
while(j<c):
  r=0
  i=0
  while(i<l):
    r+=(list[i]-j) ** 2
    i+=1
  if(r<m):
    m=r
  j+=1
print(m)