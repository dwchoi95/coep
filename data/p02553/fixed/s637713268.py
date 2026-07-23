inp = list(map(int,input().split()))
ans = []
for i in range(2):
  for j in range(2,4):
    ans.append(inp[i] * inp[j])
    
print(max(ans))