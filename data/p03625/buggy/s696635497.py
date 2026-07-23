n = int(input())
a = list(map(int,input().split()))
a.sort(reverse=True)
ans=[]
for i in range(n-1):
    if a[i]==a[i+1]:
        ans.append(a[i])
        i=i+2
if len(ans) >= 2:
    print(ans[0]*ans[1])    
else:
    print(0)
