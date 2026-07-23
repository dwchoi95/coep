n,k = map(int,input().split())
x = list(map(int,input().split()))
ans = 10**9
  
for i in range(n-k+1):
  if x[k-1+i]*x[i] < 0:
    if x[k-1+i] <= abs(x[i]) :
      temp = 2*x[k-1+i] - x[i]
    elif abs(x[i]) < x[k-1+i]:
      temp = x[k-1+i] - 2*x[i]
      
  elif (0 <= x[i]):
    temp = x[k+i-1]

  elif (x[k+i-1] <= 0):
    temp = -x[0]
    
  if temp < ans:
    ans = temp
    
print(ans)