a=[int(i) for i in input().split()]
if a[0]==sum(a[1:]) or sum(a[:2])==a[2]:
  print("Yes")
else:
  print("No")