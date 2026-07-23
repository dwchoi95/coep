s = input()
n = len(s)
temp = s[0]
grp = []
ans = [0]*n
sec = [temp]
rlind = []
for i in range(1,n):
  if temp=='L' and s[i]=='R':
    grp.append(sec)
    sec = []
  elif temp=='R' and s[i]=='L':
    rlind.append(i)
  sec.append(s[i])
  temp = s[i]
grp.append(sec)

for i in range(len(grp)):
  ind = rlind[i]
  m = len(grp[i])
  if m%2==0:
    p = m
    ans[ind]=p
    ans[ind-1]=p
  else:
    p = grp[i].count('R')
    q = max(p,m-p)
    if p==q:
      p = -(-m
    else:
      p = m
    if (q-1)%2==0:
      ans[ind]=m-p
      ans[ind-1]=p
    else:
      ans[ind]=p
      ans[ind-1]=m-p
print(*ans)