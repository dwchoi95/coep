import copy
N,K=map(int,input().split())
A=list(map(int,input().split()))
B=copy.copy(A)
ans=[]

for i in range(2**(N-1)):
    L=[0]*(N-1)
    total=0
    count=0
    for j in range(N-1):
        if ((i>>j)&1):
            L[j]=1
            count+=1
    if count>=K-1:
        A=copy.copy(B)
        for m in range(N-1):
            
            if L[m]==1:
                height=max(max(A[:m+1])+1,A[m+1])
                total+=height-A[m+1]
                A[m+1]=height
                
        ans.append(total)
        

print(min(ans))