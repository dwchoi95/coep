a=int(input())
x = 0
i = 0
while(1):
  x += a
  i += 1
  x %= 360
  if x:
    continue
  else:
    print(i)
    quit()