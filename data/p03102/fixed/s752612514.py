n,m,c=map(int,input().split())
b= [int(x) for x in input().split()]
ans=0

for i in range(n):
    a=[int(x)*y for x, y in zip(input().split(), b)]
    if(sum(a)+c>0):
        ans+=1
print(ans)