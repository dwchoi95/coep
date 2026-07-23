N,M = [int(x) for x in input().split(' ')]
AB = {}
for i in range(N):
  a,b = [int(x) for x in input().split(' ')]
  AB[a] = b
  
dc = sorted(AB.items())

c = 0
m = M
for s in dc:
  d = m - s[1]
  if d >= 0:
    m -= s[1]
    c += s[0] * s[1]
    
    if d == 0:
      break
  else:
    print(s[1] + d,"xx")
    c += s[0] * (s[1] + d)
    
    break
print(c)