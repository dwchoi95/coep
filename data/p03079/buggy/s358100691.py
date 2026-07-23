ABC = list(map(int, input().split()))
if ABC[0] + ABC[1] < ABC[2] or ABC[1] + ABC[2] < ABC[0] or ABC[0] + ABC[2] < ABC[1]:
  print("Yes")
else:
  print("No")