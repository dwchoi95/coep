n = int(input())
a = list(map(int,input().split()))
b = list(map(int,input().split()))

ans = 0

for i in range(n):
  sa = a[i] - b[i]
  
  if sa < 0:
    b[i] -= a[i]
    ans += a[i]
    sa2 = a[i+1] - b[i]
    
    if sa2 < 0:
      ans += a[i+1]
      a[i+1] = 0
    else:
      a[i+1] -= sa2
      ans += b[i]
      b[i] -= sa2
      
  else:
    ans += b[i]
    
print(ans)
    