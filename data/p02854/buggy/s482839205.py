n = int(input())
aaa = map(int, input().split())

length = 0
lengths = []
for a in aaa:
  length += a
  lengths.append(length)
  
diff = 999999
for l in lengths:
  if abs(l - (length - l)) < diff:
    diff = abs(l - (length - l))
  else:
    break
    
print(diff)