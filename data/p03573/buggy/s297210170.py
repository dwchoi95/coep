S=list(map(int,input().split()))
for i in range(2):
    if S.count(S[i])==1:
        print(S[i])