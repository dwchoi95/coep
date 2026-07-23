N = int(input())
S = str(input())
fusion = []
for i in range(N-1):
    if S[i+1] != S[i]:
        fusion +=(S[i])
fusion +=S[N-1]
print(fusion)
print(len(fusion))