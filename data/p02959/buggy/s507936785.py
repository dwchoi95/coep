N = int(input())
A = list(map(int,input().split()))
B = list(map(int,input().split()))
dp = [0 for i in range(N+1)]
if A[0] <= B[0]:
    dp[0] = A[0]
    B[0] -= A[0]
else:
    dp[0] = B[0]
    B[0] = 0



for i in range(1,N):
    if A[i] - B[i-1] >= B[i]:
        dp[i] = B[i-1] + B[i]
        B[i] = 0
    else:
        dp[i] = A[i]
        B[i] -= A[i] - B[i-1]
if A[-1] <= B[-1]:
    dp[-1] = A[-1]
    B[-1] -= A[-1]
else:
    dp[-1] = B[-1]
    B[-1] = 0
print(sum(dp))