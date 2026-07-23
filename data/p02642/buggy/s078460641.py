n = int(input())
arr = [int(x) for x in input().split()]
d = {}
for x in arr:
  d[x] = d.get(x,0)+1

mxN = 10**6 + 1
rp = [True]*mxN


for i in range(2,len(rp)):
  if i not in d or not rp[i]:continue
  for j in range(i+i,mxN,i):
    if j in d: rp[j] = False





for k,v in d.items():
  if v > 1:rp[k] = False

ans = sum([(1 if rp[x] else 0) for x in arr])
print(ans)



