N,W=map(int,input().split())
wv=[ tuple([int(j) for j in input().split()]) for _ in range(N) ]
w1=wv[0][0]
w2=w1+1
w3=w1+2 
w4=w1+3

wv=sorted(wv,key=lambda x:x[1],reverse=True)
wv=sorted(wv)
wvv = list(map(lambda x:x[1], wv))


inf = float("inf")
ans=0
from collections import defaultdict
counter = defaultdict(int)

for i in range(N):
    w,v = wv[i]
    counter[w] += 1

from bisect import bisect_left as bll

for e1 in range(0, counter[w1]+1):
  for e2 in range(0, counter[w2]+1):
    for e3 in range(0,counter[w3]+1):
      for e4 in range(0, counter[w4]+1):
          tmp=0

          if w1*e1 + w2*e2 + w3*e3 + w4*e4 > W:
              continue

          i1=bll(wv, (w1,-inf))
          i2=bll(wv, (w2,-inf))
          i3=bll(wv, (w3,-inf))
          i4=bll(wv, (w4,-inf))

          tmp= tmp \
             +sum(wvv[i1:i1+e1])  \
             +sum(wvv[i2:i2+e2])  \
             +sum(wvv[i3:i3+e3])  \
             +sum(wvv[i4:i4+e4])

          ans=max(ans,tmp)
      
print(ans)

