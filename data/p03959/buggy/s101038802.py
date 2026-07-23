N = int(input())
A = list(map(int, input().split()))
T = list(map(int, input().split()))

mod = int(1e9+7)

dp = [0] * (N)
dp[0] = 1


Amax = max(A)
Aleft, Tright = -1, -1
Tmax = max(T)
for i in range(N):
  if Amax == A[i]:
    Aleft = i
    break
for i in range(N-1,-1,-1):
  if Tmax == T[i]:
    Tright = i
    break
if Aleft > Tright:
  print(0)
  exit(0)
  
for i in range(1,N-1):
  if A[i-1] < A[i] or T[i] > T[i+1]:
    dp[i] = dp[i-1]
    if A[i] != T[i]:
      print(0)
      exit(0)
  else:
    dp[i] = dp[i-1] * min(A[i], T[i]) % mod
    
print(dp[N-2])
