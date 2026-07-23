n = int(input())
x = list(map(int, input().split()))

mini, maxi = min(x), max(x)
min2, max2 = mini**2*n, maxi**2*n
ans = max2 if max2 > min2 else min2

for p in range(mini, maxi+1):
  suma = 0
  for z in x:
    suma += (z-p)**2
  if ans > suma:
    ans = suma
    
print(ans)