
S=input()
t=10**6
for i in range(1,len(S)):
    if S[i-1]!=S[i]:
        t=min(t,max(i,len(S)-i))

if t==10**6:
    print(len(S))
else:
    print(t)
