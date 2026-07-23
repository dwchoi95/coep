x = list(map(int,input().split()))
result = None
for i in set(x):
  if x.count(i)==1:
    result = i
print(result)    