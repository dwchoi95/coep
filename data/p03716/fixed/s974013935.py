from heapq import *

N=int(input())
A=list(map(int,input().split()))
B=[]
for i in range(N):
    heappush(B,A[i])
sumB=[sum(B)]
for i in range(N,2*N):
    heappush(B,A[i])
    poped=heappop(B)
    sumB.append(sumB[-1]-poped+A[i])

A.reverse()
C=[]
for i in range(N):
    heappush(C,A[i]*(-1))
sumC=[(-1)*sum(C)]
for i in range(N,2*N):
    heappush(C,A[i]*(-1))
    poped=heappop(C)*(-1)
    sumC.append(sumC[-1]-poped+A[i])
sumC.reverse()
ans=-10**19
for i,j in zip(sumB,sumC):
    ans=max(ans,i-j)
print(ans)
