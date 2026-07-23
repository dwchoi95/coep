w,h = list(map(int,input().split()))
pq = []
for i in range(w):
    pq.append((int(input()),0))
for i in range(h):
    pq.append((int(input()),1))
pq.sort()
res = 0
w+=1
h+=1
dic = {0:w,1:h}

for x in pq:
    res += dic[1-x[1]]*x[0]
    dic[x[1]] -= 1

print(res)
