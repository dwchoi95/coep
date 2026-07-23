import math
 
s=list(map(int,input().split()))
t=list(map(int,input().split()))
a=0
b=0
c=0
d=s[1]
t.sort(reverse=True)
if s[0]==1:
  for i in range(s[1]):
    t[0]=math.floor(t[0]/2)
else:
  c=t[0]/2
  for j in range(s[1]):
    for l in range(s[0]):
      if d>0:
        if c<=t[l]:
          t[l]=math.floor(t[l]/2)
          d=d-1
        else:
            t.sort(reverse=True)
            c=t[0]/2
            continue
      else:
        break
print(sum(t))