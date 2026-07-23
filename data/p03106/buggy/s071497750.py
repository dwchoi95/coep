a,b,k=map(int, input().split())
cnt=1
for i in range(1,max(a,b)+1):
    if a%i==0 and b%i==0:
        cnt+=1
        if cnt==k:
            print(i)