

n = int(input())
a = [int(i) for i in input().split()]

from heapq import *

pq1 = a[:n]
heapify(pq1)
s = sum(pq1)
score1 = [s]
for i in range(n):
    c=heappushpop(pq1, a[n+i])
    s += a[n+i] - c
    score1.append(s)

pq2 = [-i for i in a[2*n:]]
heapify(pq2)
s = sum(pq2)
score2 = [s]
for i in range(1,n+1):
    c=heappushpop(pq2, -a[2*n-i])
    s += -a[2*n-i] - c
    score2.append(s)

print(score1)
print(score2)
ans = -10**17
for i,j in zip(score1,reversed(score2)):
    ans = max(ans, i+j)

print(ans)
    
