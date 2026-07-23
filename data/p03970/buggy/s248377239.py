S = input()
A = 'C0DEFESTIVAL2O16'
ans = 0
for i in range(len(S)):
  if S[i] == A[i]:
    ans += 1

print(ans)