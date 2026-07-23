import sys
N = int(input())
C = [0]
c = [int(sys.stdin.readline()) for i in range(N)]

C = C+c
ans = 1
dp = [0] * (N + 100)
color = [[]for i in range((2*(10**5)+100))]
dp[0] = 1

dp[1] = 1
color[C[1]].append(1)
for i in range(2, N+1):
    dp[i] = dp[i - 1]

    
    for col in reversed(color[C[i]]):
        
        if i - col == 1:
            break
        else:
            dp[i] += dp[col-1]
    
    color[C[i]].append(i)
    


print(dp[N] % (10 ** 9 + 7))



