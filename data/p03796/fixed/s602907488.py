inN = int(input())
 
D=1000000000+7
p=1
for i in range(inN):
  p*=(i+1)
  if (D < p): p=p%D
 
print(str(p))