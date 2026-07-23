n=int(input())
s=input()
count=0
for i in s:
  if i=='B':
    count+=1
if count>(n-count):
  print('Yes')
else:
  print('No')