n=int(input())
s=input()
k=0
l=set(s)
k=s[0]
ans=1
if len(l)==1:
    print("1")
    exit()
for i in range(1,n):
    if k!=s[i]:
        ans+=1
        k=s[i]
print(ans)
