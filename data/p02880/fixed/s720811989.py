num = int(input())
Flag = False
for x in range(1,10):
  for y in range(x,10):
    if x * y == num:
      Flag = True
      break
    if Flag == True:
      break

if Flag:
  print("Yes")
else:
  print("No")
