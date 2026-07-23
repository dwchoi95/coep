a,b,c = map(int,input().split())
def fib(n):
  if n == 0:
    return c
  else:
    return a * fib(n-1) -b
  
for i in range(10):
  print(fib(i+1))