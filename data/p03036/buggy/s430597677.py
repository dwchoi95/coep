r, D, x = map(int, input().split())
def mo(r, D, x, i):
  out = rx - D
  print(int(out))
  if i<9:
  	return mo(r, D, out, i+1)
  else:
    return 0
  
  mo(r, D, x, 0)