n=int(input())
s=str(input())
same=0
i=0
for i in range(n-2):
  if s[i]==s[i+1]:
    same+=1
    i+=1
print(n-same)
