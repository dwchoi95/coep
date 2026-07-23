n,m=map(int,input().split())
dic={}
doll=0
for i in range(n):
  a,b=map(int,input().split())
  dic[a]=b
  
con=sorted(dic.items())

for k,v in con:
  if v<m:
    doll+=k*v
    m-=v
  else:
    doll+=k*m
    break
print(doll)