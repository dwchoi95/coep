S=input()

start=0
for i in range(len(S)):
    start=i
    if S[i]=='B':
        break

left_W=start
ans=0
if start<len(S)-1:
    for i in range(start+1,len(S)):
        if S[i]=='W':
            ans+=i-left_W
            left_W+=1

print(ans)