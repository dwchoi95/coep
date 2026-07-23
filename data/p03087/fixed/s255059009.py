n,q = map(int,input().split())
s = list(input())
base = [0]*n
count = 0

for i in range(1,n):
  if (s[i-1] == "A") and (s[i] == "C"):
    count = count + 1
    base[i] = count
  else:
    base[i] = count

for i in range(q):
  l,r = map(int,input().split())
  ans = base[r-1] - base[l-1]
 
    
  print(ans)