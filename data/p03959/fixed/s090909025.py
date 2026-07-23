N = int(input())
T = list(map(int,input().split()))
A = list(map(int,input().split()))
ans = 1; MOD = pow(10,9)+7
if N == 1:
  if A[0] == T[0]:
    print(1)
  else:
    print(0)
  exit()
for i in range(N):
  if i == 0: 
    if A[i] == A[i+1]: 
      fac = 1
    else: 
      if A[i] > T[0]: 
        fac = 0
      else:
        fac = 1
  elif i < N-1: 
    if T[i] == T[i-1]: 
      if A[i] == A[i+1]: 
        fac = min(T[i],A[i])
      else: 
        if A[i] > T[i]: 
          fac = 0
        else:
          fac = 1
    else: 
      if A[i] == A[i+1]: 
        if T[i] > A[i]: 
          fac = 0
        else:
          fac = 1
      else: 
        if T[i] == A[i]:
          fac = 1
        else:
          fac = 0
  else: 
    if T[i] == T[i-1]: 
      if A[i] > T[i]: 
        fac = 0
      else:
        fac = 1
    else: 
      if T[i] == A[i]:
        fac = 1
      else:
        fac = 0
  ans = (ans*fac)%MOD
print(ans%MOD)
      
      
        
        
      
        
      
      
      
    