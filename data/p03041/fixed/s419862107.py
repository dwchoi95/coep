N,K=map(int,input().split())
S=list(input())
ANS=' '

S[K-1]=S[K-1].lower()

for i in S:
    ANS+=i

print(ANS)