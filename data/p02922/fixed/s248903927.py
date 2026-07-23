a,b = map(int,input().split())
c = 1 
ans = 0
while c < b:
  c += a-1
  ans += 1
print(ans)