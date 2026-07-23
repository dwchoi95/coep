s=list(input())
ans=0
wf=0
bf=0
for i in range(len(s)):
    if s[i]=='W':
        ans+=i
        wf+=1
    else:
        bf=1
if wf==0 or bf==0:
    print(0)
else:
    print(ans-wf*(wf-1)
