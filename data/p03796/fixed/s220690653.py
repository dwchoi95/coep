n = int(input())
r = 1
w = 10**9 + 7
for i in range(1, n+1):    
  r *= i
  r = (r % w)
  
  
  
print(r)