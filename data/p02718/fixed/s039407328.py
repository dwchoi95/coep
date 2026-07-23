import math
N,M = map(int,input().split())
l = [int(i) for i in input().split()]
l.sort(reverse = True)
l_sum = sum(l)
d = (1/(4*M))*l_sum
cnt = 0
 
for i in range(N):
    if l[i] >= d:
        cnt += 1
    else:
        break
 
if cnt >= M:
    print("Yes")
else:
    print("No") 