N = input()
s = input()

N1 = int(N)/2

import math
math.floor(N1)
N1= int(N1)

list_s = list(s)
list_s.sort()
X = list_s[N1]

if X=='R':
    print('Yes')
else:
    print('No')