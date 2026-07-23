s=input()
n=int(input())
ans=''
for i in range(n):
  if i%n==0:
    ans+=s[i]
print(ans)
    