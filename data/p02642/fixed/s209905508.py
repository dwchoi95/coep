n = int(input())
li = list(map(int,input().split()))
ans = 0
cnt_li = [0]*(10**6+1)

import math
import bisect
import collections
c = collections.Counter(li)
li = list(set(li))
li.sort()

for l in li:
    for x in range(2,10**7):
        if x*l > (10**6):
            break
        else:
            cnt_li[x*l] += 1


while len(li)>0:
    ba = li.pop(-1)
    if c[ba]>1:
        continue
    if cnt_li[ba] == 0:
        ans += 1
print(ans)
