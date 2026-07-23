
N=int(input())
A=list(map(int,input().split()))
A.sort(reverse=True)
ans=[]
l=0
while l<N-1:
    
    if A[l]==A[l+1]:
        ans.append(A[l])
        if len(ans)==2:
            break
        else:
            l+=2
    else:
        l+=1

if len(ans)<=1:
    print(0)
else:
    print(ans[0]*ans[1])