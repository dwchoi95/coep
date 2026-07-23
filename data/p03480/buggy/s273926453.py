


S = list(map(int, input()))




















N = len(S)

if sum(S) < 1:
    min_T = 0
else:
    min_T = N
    for i in range(1, N):
        if S[i]!=S[i-1]:
            min_T = min(min_T, max(i, N-i))

print(min_T)



