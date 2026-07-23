n,k = map(int,input().split())
a = list(map(int,input().split()))
ans = 10**11


for i in range(2**(n-1)):
  select = [0]
  len_select = 1
  for j in range(n-1):
    if i >> j & 1 and len_select < k:
      select.append(j+1)
      len_select += 1
  
  
  ok = 1
  
  for m in select:
    for l in range(n):
      if l in select: continue
      if l < m and a[l] >= a[m]:
        
        ok = 0
  if ok == 0 or len_select < k: continue
  else:
    ans_i = 0
    pre_val = a[0]
    for j in range(1,k):
      
      if pre_val >= a[select[j]]:
        ans_i += pre_val+1 - a[select[j]]
        pre_val += 1
      else:
        pre_val = a[select[j]]
  ans = min(ans,ans_i)
print(ans)