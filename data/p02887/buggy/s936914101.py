n=int(input())
s=input()

count=0
for i in range(1,n-1):
  if s[i-1]==s[i]:
    count=count+1
print(count)