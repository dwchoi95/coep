S=input()
L=len(S)
x=[1]*len(S)
for i in range(L-2):
    if S[i] == S[i+1] == "R":
        x[i+2] += x[i]
        x[i]=0
for i in range(L-1,-1,-1):
    if S[i] == S[i-1] =="L":
        x[i-2] += x[i]
        x[i]=0


print(' '.join(map(str, x)))