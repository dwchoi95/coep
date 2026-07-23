s=input()
n=len(s)
ans=-1
for i in range(n-1):
  if s[i+1]!=s[i]:   
    ans=max(ans,max(i,n-i-1))
if ans==-1:
  ans=n
print(ans)