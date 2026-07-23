s=str(input())

l=[0]*len(s)

for i in range(len(s)):
        a=s.find('L',i)
        b=s.rfind('R',0,i)
        if s[i]=='R' and (a-i)%2==0:
                l[a]+=1
        elif s[i]=='R' and (a-i)%2==1:
                l[a-1]+=1
        elif s[i]=='L' and (i-b)%2==0:
                l[b]+=1
        elif s[i]=='L' and (i-b)%2==1:
                l[b+1]+=1
print(' '.join(map(str,l)))
        