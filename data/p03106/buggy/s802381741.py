a,b,k = map(int,input().split())



c = 0
ans = 0
for i in range(min(a,b),1,-1):
  if(a%i == 0 and b%i == 0):
    c += 1
    print(i)
    if(c == k):
      ans = i
      break

print(ans)