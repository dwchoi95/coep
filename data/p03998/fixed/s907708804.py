a=list(input())
b=list(input())
c=list(input())
order='a'
while True:
  if order=='a':
    if len(a)==0:
      print('A')
      break
    else:
      order=a[0]
      a=a[1:]
  elif order=='b':
    if len(b)==0:
      print('B')
      break
    else:
      order=b[0]
      b=b[1:]
  elif order=='c':
    if len(c)==0:
      print('C')
      break
    else:
      order=c[0]
      c=c[1:]