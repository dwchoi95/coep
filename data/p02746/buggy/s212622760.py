
def solve(a,b,c,d):
  x1,y1,x2,y2=a,b,c,d
  mx=my=0
  if x1==x2 and x1%3==2:mx=1
  if y1==y2 and y1%3==2:my=1
  for i in range(29):
    x1=0--x1
    y1=0--y1
    x2=0--x2
    y2=0--y2
    if x1==x2 and x1%3==2:mx=i+2
    if y1==y2 and y1%3==2:my=i+2
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
