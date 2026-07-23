a,b,c=[int(i) for i in input().split()]
if (a+b)==c or (b+c)==a or (c+a)==b:
  print('Yes')
else:
  print('No')