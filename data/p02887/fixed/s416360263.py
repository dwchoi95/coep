N = int(input())
S = str(input())

ans = ""
ans += S[0]

for i in range(N-1):
  if S[i] != S[i+1]:
    ans += S[i+1]
print(len(ans))