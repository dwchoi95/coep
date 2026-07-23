r = int(input())
g = int(input())

if r<g:
  print(r+2*abs(r-g))
elif r>g:
  print(r-2*abs(r-g))
else:
  print(r)
