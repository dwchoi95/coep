inN = int(input())

D=1000000000 + 7
p=0
for i in range(inN):
  p*=i
  if (D < p): p=p%D

print(str(p))