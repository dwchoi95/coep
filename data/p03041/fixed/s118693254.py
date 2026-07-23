a = input().split()
b = input()
 
c = list(b)
 
for i in range(len(c)):
  if i == int(a[1]) - 1:
    c[i] = c[i].lower()
    
print(''.join(c))