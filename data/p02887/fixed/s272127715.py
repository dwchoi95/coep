N=int(input())
S=input()
d=[]
for i in range(N):
    if i==0:
        d.append(S[i])
    elif S[i]!=S[i-1]:
        d.append(S[i])
print(len(d))