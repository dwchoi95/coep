sa = list(str(input()))
sb = list(str(input()))
sc = list(str(input()))
pa, pb, pc = 0, 0, 0

read = sa[0]
while True:
  if read == 'a':
    pa += 1
    if pa == len(sa):
      print('A')
      break
    read = sa[pa]
  elif read == 'b':
    pb += 1
    if pb == len(sb):
      print('B')
      break
    read = sb[pb]
  else:
    pc += 1
    if pc == len(sc):
      print('C')
      break
    read = sc[pc]
