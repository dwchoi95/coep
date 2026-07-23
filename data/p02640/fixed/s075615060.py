x,y = map(int,input().split())
if x==1 and ( y==2 or y==4):
  print("Yes")
else:
  if y%2==1:
    print("No")
  else:
    if y<=x*4 and (y>=(x*2)):
      print("Yes")
    else:
      print("No")