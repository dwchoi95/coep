N,M=map(int,input().split())
A=list(map(int,input().split()))

ans=0
def cheap(x,y):
    x=int(x/(2**y))
    return x

i=0
while(i<M):
    sorted(A)
    A[0]=cheap(A[0],1)
    i+=1

for i in range(0,N):
    ans+=A[i]

print(ans)

