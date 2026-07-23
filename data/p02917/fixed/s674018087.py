n = int(input())
b = [int(i) for i in input().split()] 

l = [b[0]]
if n>=3:
  for i in range(0, len(b)-1):
      test =  b[i+1] - b[i]
      if test>=0:
          l.append(b[i])
      else:
          l.append(b[i+1])
  l.append(b[-1])
  print(sum(l))
else:
  print(b[0]*2)