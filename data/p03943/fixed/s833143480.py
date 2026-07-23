a=[int(i) for i in input().split()]
if a[0]==sum(a[1:]) or sum(a[:2])==a[2] or a[0]+a[2]==a[1]:
  print("Yes")
else:
  print("No")