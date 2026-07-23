N=int(input())
D=list(map(int,input().split()))
from itertools import combinations
comb=combinations(D, 2)
ans=0
for c in comb:
    ans+=c[0]*c[1]
print(ans)