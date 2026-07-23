a = [int(i) for i in input().split()] 
a.sort()
c = a[0] + a[1]
if (a[2] == c):
  print("Yes")
else:
  print("No")