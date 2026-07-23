mod=1000000007

def P(x):
    ans=1
    for i in range(x):
        ans=ans*(i+1)%mod
    
    return(ans)

n=int(input())

print(P(n))