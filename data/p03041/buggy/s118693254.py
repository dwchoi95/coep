a = input().split()
b = input()
 
list = list(b)
 
for i in list:
  if i == int(a[1]) - 1:
    list[i] = list[i].lower()
    
print(''.join(list))