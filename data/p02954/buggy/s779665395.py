s = input()
n = len(s)
temp = s[0]
group = []
ans = [0]*n
sec = [temp]
rlind = []
for i in range(1,n):
  if temp=='L' and s[i]=='R':
    group.append(sec)
    sec = []
  elif temp=='R' and s[i]=='L':
    rlind.append(i)
  sec.append(s[i])
  temp = s[i]
group.append(sec)

for i in range(len(group)):
  ind = rlind[i]
  m = len(group[i])
  if m%2==0:
    p = m
    ans[ind]=p
    ans[ind-1]=p
  else:
    p = group[i].count('R')
    q = max(p,m-p)
    if (q-1)%2==0:
      ans[ind]=m-p
      ans[ind-1]=p
    else:
      ans[ind]=p
      ans[ind-1]=m-p
print(*ans)