S = input()
j = 0
m = S[0]
ls = []
for i in range(len(S)):
  if m!=S[i]:
    ls += [i-j]
    j = i
    m = S[i]
ls += [len(S)-j]
if len(ls)<3:
  print(max(ls))
else:
  ans = 0
  for i in range(0,len(ls)-2):
    m = min(ls[i]+ls[i+1],ls[i+1]+ls[i+2])
    ans = max(ans,m)
  print(ans)