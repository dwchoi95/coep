x,y=map(int,input().split())
len=1
while True:
  if x*2<=y:
    len+=1
  else:
    break
  x*=2
print(len)