s=input()
m=[s[i]=="B" for i in range(len(s))]
m1=[None for i in range(len(s))]
m1[0]=m[0]
for i in range(1,len(s)):
  m1[i]=m1[i-1]+m[i]
m2=[None for i in range(len(s))]
m2[len(s)-1]=m[len(s)-1]
for i in range(len(s)-1,0,-1):
  m2[i-1]=m2[i]+m[i]
  
ans1=0
ans2=0
for i in range(1,len(s)):
  if s[i]=="W":
    ans1+=m1[i]
    ans2+=m2[i]
    
print(ans1)

