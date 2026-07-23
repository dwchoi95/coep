
N=int(input())
A=list(map(int,input().split()))
A.sort(reverse=True)
cnt=1
ans=[]
for i in range(N-1):
    
    if A[i]==A[i+1]:
        cnt+=1
    elif cnt>=2:
        ans.append(A[i-1])
        cnt=1
        if len(ans)==2:
            break

if len(ans)<=1:
    print(0)
else:
    print(ans[0]*ans[1])