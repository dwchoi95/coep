S=input()

num={}
for i in range(len(S)):
    num[i]=0

for i in range(1,len(S)):
    even=1
    odd=1
    if S[i]=='L' and S[i-1]=='R':

        j=1
        while(1):
            if i+j>(len(S)-1):
                break
            if S[i+j]=='L':
                if j%2==1:
                    odd+=1
                else:
                    even+=1
            else:
                break
            j+=1
        
        j=1
        while(1):
            if i-1-j<0:
                break
            if S[i-1-j]=='R':
                if j%2==1:
                    even+=1
                else:
                    odd+=1
            else:
                break
            j+=1

        num[i]=even
        num[i-1]=odd

for i in range(len(S)):
    print(num[i],end=' ')
print('')