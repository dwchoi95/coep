x,y=map(int,input().split())
len=1
while True:
  x*=2
  if x*2<y:
    len+=1
  else:
    break
print(len)