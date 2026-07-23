N=int(input())
D=list(map(int,input().split()))
from itertools import combinations
ans=0
comb=combinations(D,2)
for c in comb:
  ans+=c[0]+c[1]
print(ans)