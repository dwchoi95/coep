a,b = map(int,input().split())
sum = 1
count = 0
while sum < b :
  sum += a - 1
  count += 1
print (count)