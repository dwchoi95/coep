X, Y = map(int, input().split())
c = 1
while(True):
  if X <= Y:
    X *= 2
    c += 1
  else:
    break
print(c)