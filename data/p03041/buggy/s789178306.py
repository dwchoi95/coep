n,k = map(int,input().split())
s = str(input())
ans = ''
for i in range(len(s)):
  if i == k:
    ans = ans + s[i].lower()
  else:
    ans = ans + s[i]
print (ans)