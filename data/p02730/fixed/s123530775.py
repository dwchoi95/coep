S = input()
n = len(S)




if S[:int((n-1)/2)] == S[:int((n-1)/2)][::-1] and S[int((n+1)/2):]== S[int((n+1)/2):][::-1] and S[:int((n-1)/2)] == S[int((n+1)/2):][::-1]:
  print("Yes")
else:
  print("No")