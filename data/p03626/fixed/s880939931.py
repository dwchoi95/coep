n = int(input())
s1 = str(input())
s2 = str(input())
mod = 10**9+7
if s1[0] == s2[0]:
  c = 3
  state = True
  i = 1
else:
  c = 6
  state = False
  i = 2
while i < n:
  if s1[i] == s2[i]:
    i += 1
    if state:
      c *= 2
    else:
      state = True
  else:
    i += 2
    if state:
      c *= 2
      state = False
    else:
      c *= 3
print(c%(mod))
  
  