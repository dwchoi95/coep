import heapq

N,M=map(int,input().split())
A=list(map(int,input().split()))
for i in range (0,len(A)):
    A[i]*=-1

heapq.heapify(A)

ans=0
def cheap(x,y):
    x=int(x/(2**y))
    return x

i=0
while(i<M):
    tmp=heapq.heappop(A)
    tmp=cheap(tmp,1)
    heapq.heappush(A,tmp)
    i+=1

for i in range(0,N):
    ans+=A[i]

print(ans*(-1))

