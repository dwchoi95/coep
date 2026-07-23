a=list(input())
b=list(input())
c=list(input())
order='a'
while True:
  if order=='a':
    order=a[0]
    if len(a)==1:
      print('A')
      break
    else:
      a=a[1:]
  elif order=='b':
    order=b[0]
    if len(b)==1:
      print('B')
      break
    else:
      b=b[1:]
  elif order=='c':
    order=c[0]
    if len(c)==1:
      print('C')
      break
    else:
      c=c[1:]