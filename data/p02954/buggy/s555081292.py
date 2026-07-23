import math

S = input()

l = [0]
ans = [0]*len(S)

tmp = "R"
for i in range(len(S)):
  if tmp != S[i]:
    l.append(i)
  tmp = S[i]

l.append(len(S))

for i in range(1, len(l), 2):
  ans[l[i]-1] = math.ceil((l[i]-l[i-1])/2) + math.floor((l[i+1]-l[i])/2)
  ans[l[i]] = math.floor((l[i]-l[i-1])/2) + math.ceil((l[i+1]-l[i])/2)

print(ans)