r = int(input())
g = int(input())

if r<g:
  print(2*abs(r-g)+r)
elif r>g:
  print(2*abs(r-g)-r)
else:
  print(r)
