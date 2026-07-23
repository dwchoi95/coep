a,b,c = map(int,input().split())
def fib(n):
  if n == 0:
    return c
  else:
    return 2 * fib(n-1) -10
  
for i in range(10):
  print(fib(i+1))