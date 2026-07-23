n = int(input())
li = list(map(int,input().split()))
ans = 0

import math
import bisect
import collections
c = collections.Counter(li)
li = list(set(li))

while len(li)>0:
    ba = li.pop(-1)
    if c[ba]>1:
        continue
    
    
    tmp_li = li
    
    for tt in tmp_li:
        if ba%tt == 0:
            break
    else:
        ans += 1
print(ans)