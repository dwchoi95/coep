h,w=map(int,input().split())
if h == 1 or w == 1:
  print(1)
elif h%2 == 0 or w%2 == 0:
  print(h*w/2)
else:
  print(int(h*w/2)+1)
  
