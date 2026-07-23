n,k = list(map(int, input().split()))
a=list(map(int, input().split()))

ans=[]
for i in range(1<<n):
    
    if bin(i).count("1")==k:
        cst=0
        use=a.copy()
        for u in range(1,n):
            if(i>>u&1):
                left_max=max(use[:u])
                cst+=left_max-use[u]+1
                use[u]= left_max+1
        ans.append(cst)   
print(min(ans))
