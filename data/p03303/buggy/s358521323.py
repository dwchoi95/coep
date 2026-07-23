s=list(input())
w=int(input())
x=[]
y=''
ans=''
count=[]
for i in range(len(s)):
    y+=s[i]
    if len(list(y))==w:
        x.append(y)
        y=''
    if i==len(s)-1:
        x.append(y)
for j in range(len(x)-1):
    count=list(x[j])
    ans+=count[0]
print(ans)
