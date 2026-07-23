S=list(map(int,input().split()))
for i in range(3):
    if S.count(S[i])==1:
        print(S[i])