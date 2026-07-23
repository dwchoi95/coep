
def check(lv,aa,bb,cc,dd,xy):
  a,b,c,d=aa,bb,cc,dd
  if a>c:a,c=c,a
  if b>d:b,d=d,b
  mi=3**(lv-1)
  ma=2*3**(lv-1)+1
  aa=0--a
  bb=0--b
  cc=0--c
  dd=0--d
  if xy=="y":
    if bb==dd and bb%3==2:return False
    return (a<=mi and ma<=c and mi<b<=d<ma)
  else:
    if aa==cc and cc%3==2:return False
    return (b<=mi and ma<=d and mi<a<=c<ma)
def solve(a,b,c,d):
  mx=my=0
  for i in range(1,31):
    if check(i,a,b,c,d,"x"):mx=i
    if check(i,a,b,c,d,"y"):my=i
  if mx<my:
    ans=abs(a-c)
    mi=3**(my-1)
    ma=2*3**(my-1)+1
    ans+=min(abs(mi-b)+abs(mi-d),abs(ma-b)+abs(ma-d))
    return ans
  if mx>my:
    ans=abs(b-d)
    mi=3**(mx-1)
    ma=2*3**(mx-1)+1
    ans+=min(abs(mi-a)+abs(mi-c),abs(ma-a)+abs(ma-c))
    return ans
  if mx==my==0:return abs(a-c)+abs(b-d)
  ans=1/0
q=int(input())
for _ in range(q):
  a,b,c,d=map(int,input().split())
  print(solve(a,b,c,d))
