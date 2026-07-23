S=input()

start=0
for i in range(len(S)):
    if S[i]=='B':
        break

    start=i

left_W=start
ans=0
if start<len(S)-1:
    for i in range(start+1,len(S)):
        if S[i]=='W':
            ans+=i-left_W
            left_W+=1

print(ans)