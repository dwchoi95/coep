a = list(input())
b = list(input())
c = list(input())
moji = a[0]
select = "a"
lengtha = len(a)
lengthb = len(b)
lengthc = len(c)
while True:
  if select == "a":
    if lengtha == 0:
      print("A")
      break;
    else:
      select = a[0]
      del a[0]
      lengtha -= 1
  elif select == "b":
    if lengthb == 0:
      print("B")
      break;
    else:
      select = b[0]
      del b[0]
      lengthb -= 1
  else:
    if lengthc==0:
      print("C")
      break;
    else:
      select = c[0]
      del c[0]
      lengthc -= 1