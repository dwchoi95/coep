s=str(input())

l=[0]*len(s)

for i in range(len(s)):
        if s[i]=='R' and i%2==1:
                a=s.find('L',i)
                l[a-1]+=1
        elif s[i]=='R' and i%2==0:
                a=s.find('L',i)
                l[a]+=1
        elif s[i]=='L' and i%2==1:
                a=s.rfind('R',0,i)
                l[a]+=1
        elif s[i]=='L' and i%2==0:
                a=s.rfind('R',0,i)
                l[a+1]+=1
print(' '.join(map(str,l)))
        