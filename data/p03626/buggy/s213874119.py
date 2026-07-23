import sys

import math







mod=1000000007
n=int(input())
s=[input() for _ in range(2)]
d=[]
i=0
while i<n:
    if s[0][i]==s[1][i]:
        d.append(1)
        i+=1
    else:
        d.append(2)
        i+=2
m=len(d)
ans=0
if d[0]==1:
    ans=3
if d[0]==2:
    ans=6
print(d)
for i in range(1,m):
    if d[i]==1:
        if d[i-1]==2:
            ans*=1
        else:
            ans*=2
    else:
        if d[i-1]==2:
            ans*=3
        else:
            ans*=2
    ans=ans%mod
print(ans%mod)