a,b = map(int,input().split()) 
c = 0
for i in range(1,10):
  for j in range(0,10):
    for k in range(0,10):
      x = 10001*i+1010*j+100*k
      if x >= a and x <= b:
        c += 1