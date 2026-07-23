n=int(input())
b=list(map(int,input().split()))
ans=[]
for j in range(n-2):
    ans.append(min(b[j],b[j+1]))

print(sum(ans)+b[0]+b[-1])