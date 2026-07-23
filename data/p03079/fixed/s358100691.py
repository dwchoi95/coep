ABC = list(map(int, input().split()))
if ABC[0] == ABC[1] and ABC[1]==ABC[2] and ABC[2]==ABC[0]:
  print("Yes")
else:
  print("No")
