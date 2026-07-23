n=int(input())
x=list(map(int,input().split()))
my_round_int = lambda y: int((y * 2 + 1) 
ans=sum(x)/n
ans=my_round_int(ans)
v=0
for i in x:
    v+=(i-ans)**2
print(v)
