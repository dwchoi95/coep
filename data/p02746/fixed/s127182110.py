def solve(aa,bb,cc,dd):
  a,b,c,d=aa,bb,cc,dd
  mx=my=0
  for i in range(1,31):
    if a==c and a%3==2 and abs(b-d)>=2:mx=i
    if b==d and b%3==2 and abs(a-c)>=2:my=i
    a=0--a
    b=0--b
    c=0--c
    d=0--d
  a,b,c,d=aa,bb,cc,dd
  if mx==my==0:return abs(a-c)+abs(b-d)
  if mx<my:
    ans=abs(a-c)
    mi=3**(my-1)
    ma=2*3**(my-1)+1
    bd=(3**my)*((0--b
    b-=bd
    d-=bd
    ans+=min(abs(mi-b)+abs(mi-d),abs(ma-b)+abs(ma-d))
    return ans
  if mx>my:
    ans=abs(b-d)
    mi=3**(mx-1)
    ma=2*3**(mx-1)+1
    ac=(3**mx)*((0--a
    a-=ac
    c-=ac
    ans+=min(abs(mi-a)+abs(mi-c),abs(ma-a)+abs(ma-c))
    return ans
  if mx==my==0:return abs(a-c)+abs(b-d)
  ans=1/0
q=int(input())
for _ in range(q):
  a,b,c,d=map(int,input().split())
  print(solve(a,b,c,d))