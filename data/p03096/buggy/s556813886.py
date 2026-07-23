N = int(input())
C = [0] * N
mod = 10 ** 9 + 7
dic = {}
for i in range(N):
    C[i] = int(input())
    if not C[i] in dic:
        dic[C[i]] = [ i ]
    else:
        dic[C[i]].append(i)

dp = [0] * N
dp[0] = 1
for i in range(1,N):
    dp[i] = dp[i-1]
    if C[i] == C[i-1]:
        continue

    for prev in dic[C[i]]:
        if prev < i:
            if prev > 0:
                dp[i] += dp[prev-1]
            else:
                dp[i] += 1

print(dp[N-1])