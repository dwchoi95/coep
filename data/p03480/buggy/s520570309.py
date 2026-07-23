S = input()

s = S[0]
temp_T = 100000
for i in range(1, len(S)):
    if(S[i] != s):
        judge = max(i,len(S)-i)
        temp_T = min(judge, temp_T)
        s = S[i]

print(temp_T)
