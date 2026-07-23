s=input();l=[]
for i in range(len(s)-1):
 if s[i]!=s[i+1]:l+=[max(i+1,len(s)-i-1)]
print(min(l)if l else 1)