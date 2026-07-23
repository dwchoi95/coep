N=int(input())
list = list(map(int, input().split()))

l=len(list)
m=0
i=0
j=1
r=0

while(i<l):
  if(m < abs(list[i]-j)):
    m = j
  i+=1
  j+=1

k=0

while(k<l):
  r+=abs(list[k]-m)*abs(list[k]-m)
  k+=1

print(r)