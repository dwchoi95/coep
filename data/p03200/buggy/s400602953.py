hoge=input()
ans=0
count=0
white=0
for i in hoge:
  
  if(i=="W"):
    ans+=count - white
    white+=1
  count+=1
  
print(count)