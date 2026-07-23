x,y = map(int, input().split())
ans=0
for i in range(x):
  if (y-i*2)/2<=x:
    ans=1
if ans:
  print('Yes')
else:
  print('No')