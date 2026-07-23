S=input()

num={}
for i in range(len(S)):
    num[i]=0

for i in range(len(S)):
    if S[i]=='L' and S[i-1]=='R':
        j=1
        count=1
        while(1):
            if i-j<0:
                break
            if S[i-j]=='R':
                if j%2==0:
                    count+=1
            else:
                break
            j+=1
        num[i]=count

for i in range(len(S)):
    if S[i]=='R' and S[i+1]=='L':
        j=1
        count=1
        while(1):
            if i+j>len(S)-1:
                break
            if S[i+j]=='L':
                if j%2==0:
                    count+=1
            else:
                break
            j+=1
        num[i]=count


for i in range(len(S)):
    print(num[i],end=' ')

print('')