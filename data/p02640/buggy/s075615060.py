x,y = map(int,input().split())
if x==1 and y==2 and y==4:
  print("Yes")
else:
  if y%2==1:
    print("No")
  else:
    if y<=x*4:
      print("Yes")
    else:
      print("No")