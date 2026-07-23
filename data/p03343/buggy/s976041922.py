import bisect
n,k,q = map(int,input().split())
a = list(map(int,input().split()))
if q == 1:
  print(0)
  exit()
ls = [-1,n]
b = sorted(((a[i],i) for i in range(n)))
ansls = [b[q-1][0]-b[0][0]]
for i,x in enumerate(b):
  ins = bisect.bisect_left(ls,i)
  ls.insert(ins,i)
  space = []
  qc = q-1
  for j in range(1,i+3):
    space.append(ls[j]-ls[j-1]-1)
  for j in range(i+1,n):
    idx = bisect.bisect_left(ls,b[j][1])
    if space[idx-1] < k:
      continue
    qc -= 1
    space[idx-1] -= 1
    if qc == 0:
      ansls.append(b[j][0]-x[0])
      break
print(min(ansls))