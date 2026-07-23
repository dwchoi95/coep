n=int(input())

t=list(map(int,input().split()))
a=list(map(int,input().split()))


kakute=[0]*n
kakute[0]=1

if n==1:
    if t[0]!=a[0]:
        print(0)
        exit()

for i in range(1,n):
    if t[i]>t[i-1]:
        kakute[i]=1

a=a[::-1]
ans=1

for i in range(1,n):
    index=n-i-1
    
    if a[i]>a[i-1]:
        
        if a[i]>t[index]:
            print(0)
            exit()
        
        elif kakute[index]==1:
            if a[i] != t[index]:
                print(0)
                exit()
    
    else:
        
        if kakute[index]==1:
            if t[index]>a[i]:
                print(0)
                exit()
        
        else:
            ans=ans*min(a[i],t[index])%(10**9+7)

print(ans%(10**9+7))


            

        







