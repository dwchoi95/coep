S = input()


temp_T = len(S)
for i in range(len(S)-1):
    if(S[i] != S[i+1]):
        judge = max(i+1,len(S)-(i+1))
        temp_T = min(judge, temp_T)

print(temp_T)
