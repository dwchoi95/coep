N,M = [int(x) for x in input().split(' ')]
AB = {}
for i in range(N):
  a,b = [int(x) for x in input().split(' ')]
  if a in AB:
    AB[a] += b
  else:
    AB[a] = b
    
dc = sorted(AB.items())

c = 0
m = M
for s in dc:
  price, stock = s
  if stock >= m:
    c += price * m
    break
  else:
    c += stock * price
    m -= stock
    
print(c)
    