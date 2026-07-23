n,q = map(int,input().split())
s = list(input())
base = [0]*n
count = 0

for i in range(n-1):
  if (s[i] == "A") and (s[i+1] == "C"):
    count = count + 1
    base[i] = count
  else:
    base[i] = count

base[n-1] = base[n-2]

for i in range(q):
  l,r = map(int,input().split())
  ans = base[r-1] - base[l-1]
  
  if s[r-1] == "A":
    ans = ans - 1
  
  if s[l-1] == "A":
    ans = ans + 1
    
  print(ans)