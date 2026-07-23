n = int(input())
aaa = map(int, input().split())

length = 0
lengths = []
for a in aaa:
  length += a
  lengths.append(length)
  
diffs = []
for l in lengths:
  diff = abs(l - (length - l))
  diffs.append(diff)
    
print(min(diffs))