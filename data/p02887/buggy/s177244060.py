n=int(input())
s=list(input())
prev=s[0]
sum=1
for i in range(n-1):
    if(prev!=s[i]):
        sum+=1
    prev=s[i]
print(sum)