a = list(input())
b = list(input())
c = list(input())
select = "a"
lengtha = len(a)
lengthb = len(b)
lengthc = len(c)
while True:
  if select == "a":
    del a[0]
    lengtha -= 1
    if lengtha == 0:
      print("A")
      break;
    else:
      select = a[0]
  elif select == "b":
    del b[0]
    lengthb -= 1
    if lengthb == 0:
      print("B")
      break;
    else:
      select = b[0]
  else:
    del c[0]
    lengthc -= 1
    if lengthc==0:
      print("C")
      break;
    else:
      select = c[0]