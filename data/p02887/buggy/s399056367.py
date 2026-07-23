N = int(input())
S = str(input())

ans = [S[-1]]

for i in range(N):
    if(ans[-1] != S[i]):
        ans.append(S[i])

print(len(ans))
