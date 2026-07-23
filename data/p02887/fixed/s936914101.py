n=int(input())
s=input()

count=1
for i in range(1,n):
  if s[i-1]==s[i]:
    count=count+0
  else:
    count+=1
print(count)