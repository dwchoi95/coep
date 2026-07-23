S = input()
a = S.count('N')
b = S.count('S')
c = S.count('E') 
d = S.count('W')

if a*b*c*d > 0:
  print('Yes')
elif a*b > 0 and c==0 and d==0:
  print('Yes')
elif c*d >0 and a==0 and b==0:
  print('Yes')
elif a==0 and b==0 and c==0 and d==0:
  print('Yes')
else:
  print('No')