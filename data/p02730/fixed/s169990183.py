S=str(input())
N=len(S)

S1 = S[0:int((N-1)/2)]
S2 = S[int((N+3)/2)-1:N]

if S==S[::-1] and S1==S1[::-1] and S2==S2[::-1]:
  print("Yes")
else:
  print("No")